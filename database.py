"""
CyberHeist Bot - Database Layer

Single source of truth untuk SQLite operations. Semua cogs call functions di sini,
tidak ada raw SQL di tempat lain. Data player bersifat global (satu wallet per user_id,
lintas server Discord).
"""

import sqlite3
import os
import time
from contextlib import contextmanager

import config
from logger import get_logger

logger = get_logger(__name__)


def init_db():
    """
    Inisialisasi database dan jalankan migrations otomatis (guild_id removal,
    jail_until, daily reward columns).
    """
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id          INTEGER PRIMARY KEY,
                bytes            INTEGER NOT NULL DEFAULT 0,
                level            INTEGER NOT NULL DEFAULT 1,
                xp               INTEGER NOT NULL DEFAULT 0,
                heat             INTEGER NOT NULL DEFAULT 0,
                rig_level        INTEGER NOT NULL DEFAULT 0,
                jail_until       INTEGER NOT NULL DEFAULT 0,
                last_daily_claim INTEGER NOT NULL DEFAULT 0,
                daily_streak     INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()

        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]

        # Migration 1: merge multi-server data to single wallet per user_id
        if "guild_id" in existing_columns:
            logger.info("Migration: removing guild_id schema, merging to global wallet...")
            conn.execute("""
                CREATE TABLE players_new (
                    user_id     INTEGER PRIMARY KEY,
                    bytes       INTEGER NOT NULL DEFAULT 0,
                    level       INTEGER NOT NULL DEFAULT 1,
                    xp          INTEGER NOT NULL DEFAULT 0,
                    heat        INTEGER NOT NULL DEFAULT 0,
                    rig_level   INTEGER NOT NULL DEFAULT 0,
                    jail_until  INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                INSERT INTO players_new (user_id, bytes, level, xp, heat, rig_level, jail_until)
                SELECT
                    user_id,
                    SUM(bytes),
                    MAX(level),
                    MAX(xp),
                    MAX(heat),
                    MAX(rig_level),
                    MAX(jail_until)
                FROM players
                GROUP BY user_id
            """)
            conn.execute("DROP TABLE players")
            conn.execute("ALTER TABLE players_new RENAME TO players")
            conn.commit()
            logger.info("Migration guild_id complete.")

        # Migration 2: add jail_until column if missing
        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]
        if "jail_until" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN jail_until INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: 'jail_until' column added.")

        # Migration 3: add daily reward columns
        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]
        if "last_daily_claim" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN last_daily_claim INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: 'last_daily_claim' column added.")

        if "daily_streak" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN daily_streak INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: 'daily_streak' column added.")

    logger.info("Database ready.")


@contextmanager
def get_connection():
    """SQLite connection with WAL mode and 10s timeout for concurrent access."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


# Player: create & read

def get_player(user_id: int) -> sqlite3.Row:
    """Fetch player data, auto-create if not exists (thread-safe)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT OR IGNORE INTO players (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM players WHERE user_id = ?", (user_id,)
            ).fetchone()

        return row


# Player: bytes (currency)

def add_bytes(user_id: int, amount: int):
    """Add or subtract bytes (clamped to 0)."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = MAX(0, bytes + ?) WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


def set_bytes(user_id: int, amount: int):
    """Set bytes to exact value."""
    get_player(user_id)
    amount = max(0, amount)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


# Player: XP & level

def add_xp(user_id: int, amount: int) -> dict:
    """Add XP and auto-process level-ups. Returns level-up info dict."""
    player = get_player(user_id)
    current_level = player["level"]
    current_xp = player["xp"] + amount

    old_level = current_level
    leveled_up = False

    while current_xp >= config.xp_required_for_level(current_level):
        current_xp -= config.xp_required_for_level(current_level)
        current_level += 1
        leveled_up = True

    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET xp = ?, level = ? WHERE user_id = ?",
            (current_xp, current_level, user_id),
        )
        conn.commit()

    return {
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_level": current_level,
        "current_xp": current_xp,
    }


def set_level(user_id: int, level: int, xp: int = 0):
    """Set level and XP to exact values."""
    get_player(user_id)
    level = max(1, level)
    xp = max(0, xp)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET level = ?, xp = ? WHERE user_id = ?",
            (level, xp, user_id),
        )
        conn.commit()


# Player: heat

def add_heat(user_id: int, amount: int) -> dict:
    """
    Add/subtract heat (clamped 0-100). Arrest triggers only on positive increase
    reaching 100: reset heat, fine bytes, set jail_until.
    """
    player = get_player(user_id)
    current_heat = player["heat"]
    new_heat = current_heat + amount

    arrested = False
    fine = 0
    jail_until = player["jail_until"]

    if amount > 0 and new_heat >= config.HEAT_MAX:
        arrested = True
        new_heat = 0

        current_bytes = player["bytes"]
        if current_bytes > 0:
            fine = max(
                config.HEAT_ARREST_FINE_MINIMUM,
                round(current_bytes * config.HEAT_ARREST_FINE_PERCENTAGE),
            )
            fine = min(fine, current_bytes)

        jail_until = int(time.time()) + config.JAIL_COOLDOWN_SECONDS
    else:
        new_heat = max(config.HEAT_MIN, min(config.HEAT_MAX, new_heat))

    with get_connection() as conn:
        if arrested:
            conn.execute(
                """UPDATE players
                   SET heat = ?, bytes = MAX(0, bytes - ?), jail_until = ?
                   WHERE user_id = ?""",
                (new_heat, fine, jail_until, user_id),
            )
        else:
            conn.execute(
                "UPDATE players SET heat = ? WHERE user_id = ?",
                (new_heat, user_id),
            )
        conn.commit()

    return {
        "heat": new_heat,
        "arrested": arrested,
        "fine": fine,
        "jail_until": jail_until if arrested else 0,
    }


def clear_jail(user_id: int):
    """Clear jail status (set jail_until = 0)."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET jail_until = 0 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def is_jailed(user_id: int) -> dict:
    """Check if player is still jailed (cooldown after arrest)."""
    player = get_player(user_id)
    jail_until = player["jail_until"]
    now = int(time.time())

    if jail_until > now:
        return {"jailed": True, "seconds_remaining": jail_until - now}

    return {"jailed": False, "seconds_remaining": 0}


def set_heat(user_id: int, value: int):
    """Set heat directly (0-100) without triggering jail logic."""
    get_player(user_id)
    value = max(config.HEAT_MIN, min(config.HEAT_MAX, value))
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET heat = ? WHERE user_id = ?",
            (value, user_id),
        )
        conn.commit()


# Player: rig level

def set_rig_level(user_id: int, rig_level: int):
    """Set rig_level to specific value."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET rig_level = ? WHERE user_id = ?",
            (rig_level, user_id),
        )
        conn.commit()


def get_players_with_heat() -> list:
    """Fetch all players with heat > 0 for passive decay."""
    with get_connection() as conn:
        return conn.execute("SELECT user_id, heat FROM players WHERE heat > 0").fetchall()

def get_leaderboard(limit: int = 10):
    """Fetch top players by bytes (global leaderboard)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM players ORDER BY bytes DESC LIMIT ?", (limit,)
        ).fetchall()
        return rows


# Admin / maintenance

def reset_player(user_id: int):
    """Delete all player data (reset to new player state)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
        conn.commit()


def get_economy_stats() -> dict:
    """Economy stats: total players, total bytes, averages."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total_players,
                COALESCE(SUM(bytes), 0) AS total_bytes,
                COALESCE(AVG(level), 0) AS avg_level,
                COALESCE(AVG(bytes), 0) AS avg_bytes
            FROM players
        """).fetchone()

        return {
            "total_players": row["total_players"],
            "total_bytes": row["total_bytes"],
            "avg_level": round(row["avg_level"], 1),
            "avg_bytes": round(row["avg_bytes"], 1),
        }


# Daily reward system

def get_daily_status(user_id: int) -> dict:
    """Check daily reward status: can claim, current streak, seconds until reset."""
    player = get_player(user_id)
    current_day = int(time.time()) // 86400
    last_claim_day = player["last_daily_claim"]
    current_streak = player["daily_streak"]

    can_claim = last_claim_day < current_day
    is_streak_continued = (last_claim_day == current_day - 1)
    next_streak = (current_streak + 1) if is_streak_continued else 1

    next_reset_timestamp = (current_day + 1) * 86400
    seconds_until_reset = next_reset_timestamp - int(time.time())

    return {
        "can_claim": can_claim,
        "current_streak": current_streak,
        "next_streak": next_streak,
        "seconds_until_reset": seconds_until_reset,
        "last_claim_day": last_claim_day,
        "current_day": current_day,
    }


def claim_daily_reward(
    user_id: int,
    base_bytes: int,
    streak_bonus: int,
    bonus_type: str,
    bonus_value: int
) -> dict:
    """
    Atomic daily reward claim. Returns dict with success status and reward details.
    bonus_type: "extra_bytes" | "xp" | "heat" | "cipher"
    """
    get_player(user_id)
    current_day = int(time.time()) // 86400

    with get_connection() as conn:
        # Hitung streak baru
        daily_status = get_daily_status(user_id)
        if not daily_status["can_claim"]:
            return {"success": False, "reason": "already_claimed"}

        new_streak = daily_status["next_streak"]
        total_bytes_gain = base_bytes + streak_bonus

        if bonus_type in ["extra_bytes", "cipher"]:
            total_bytes_gain += bonus_value

        cursor = conn.execute(
            """UPDATE players
               SET last_daily_claim = ?,
                   daily_streak = ?,
                   bytes = bytes + ?
               WHERE user_id = ? AND last_daily_claim < ?""",
            (current_day, new_streak, total_bytes_gain, user_id, current_day)
        )

        if cursor.rowcount == 0:
            return {"success": False, "reason": "already_claimed"}

        conn.commit()

    level_up_result = None
    new_heat = None

    if bonus_type == "xp":
        level_up_result = add_xp(user_id, bonus_value)

    elif bonus_type == "heat":
        heat_result = add_heat(user_id, -bonus_value)
        new_heat = heat_result["heat"]

    return {
        "success": True,
        "base_bytes": base_bytes,
        "streak_bonus": streak_bonus,
        "bonus_type": bonus_type,
        "bonus_value": bonus_value,
        "total_bytes_gain": total_bytes_gain,
        "new_streak": new_streak,
        "level_up_result": level_up_result,
        "new_heat": new_heat,
    }


def admin_reset_daily(user_id: int):
    """Reset last_daily_claim to 0 for testing."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET last_daily_claim = 0 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()


def admin_set_streak(user_id: int, streak: int):
    """Set daily_streak to specific value."""
    get_player(user_id)
    streak = max(0, min(999999, streak))
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET daily_streak = ? WHERE user_id = ?",
            (streak, user_id)
        )
        conn.commit()