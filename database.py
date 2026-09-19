"""
CyberHeist Bot - Database Layer
==================================
File ini adalah satu-satunya tempat yang berurusan langsung dengan SQLite.
Semua cogs (hack, shop, profile, dll) akan memanggil fungsi-fungsi di
file ini, TIDAK PERNAH menulis query SQL mentah di file lain.
Tujuannya: kalau nanti kita ganti struktur tabel, cukup ubah di sini.
"""

import sqlite3
import os
import time
from contextlib import contextmanager

import config


def init_db():
    """
    Membuat folder data/ (kalau belum ada) dan tabel `players`
    (kalau belum ada). Dipanggil sekali saat bot pertama kali start.
    """
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id     INTEGER,
                guild_id    INTEGER,
                bytes       INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                heat        INTEGER NOT NULL DEFAULT 0,
                rig_level   INTEGER NOT NULL DEFAULT 0,
                jail_until  INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        conn.commit()
    print("[DB] Database siap. Tabel 'players' sudah ada/dibuat.")


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


# =========================================================
# PLAYER: CREATE & READ
# =========================================================

def get_player(user_id: int, guild_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO players (user_id, guild_id) VALUES (?, ?)", (user_id, guild_id)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)
            ).fetchone()

        return row


# =========================================================
# PLAYER: BYTES (currency)
# =========================================================

def add_bytes(user_id: int, guild_id: int, amount: int):
    get_player(user_id, guild_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = bytes + ? WHERE user_id = ? AND guild_id = ?",
            (amount, user_id, guild_id),
        )
        conn.commit()


def set_bytes(user_id: int, guild_id: int, amount: int):
    get_player(user_id, guild_id)
    amount = max(0, amount)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = ? WHERE user_id = ? AND guild_id = ?",
            (amount, user_id, guild_id),
        )
        conn.commit()


# =========================================================
# PLAYER: XP & LEVEL
# =========================================================

def add_xp(user_id: int, guild_id: int, amount: int) -> dict:
    player = get_player(user_id, guild_id)
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
            "UPDATE players SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
            (current_xp, current_level, user_id, guild_id),
        )
        conn.commit()

    return {
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_level": current_level,
        "current_xp": current_xp,
    }


def set_level(user_id: int, guild_id: int, level: int, xp: int = 0):
    get_player(user_id, guild_id)
    level = max(1, level)
    xp = max(0, xp)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET level = ?, xp = ? WHERE user_id = ? AND guild_id = ?",
            (level, xp, user_id, guild_id),
        )
        conn.commit()


# =========================================================
# PLAYER: HEAT
# =========================================================

def add_heat(user_id: int, guild_id: int, amount: int) -> dict:
    player = get_player(user_id, guild_id)
    current_heat = player["heat"]
    new_heat = current_heat + amount

    arrested = False
    fine = 0
    jail_until = player["jail_until"]

    if new_heat >= config.HEAT_MAX:
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
                   SET heat = ?, bytes = bytes - ?, jail_until = ?
                   WHERE user_id = ? AND guild_id = ?""",
                (new_heat, fine, jail_until, user_id, guild_id),
            )
        else:
            conn.execute(
                "UPDATE players SET heat = ? WHERE user_id = ? AND guild_id = ?",
                (new_heat, user_id, guild_id),
            )
        conn.commit()

    return {
        "heat": new_heat,
        "arrested": arrested,
        "fine": fine,
        "jail_until": jail_until if arrested else 0,
    }


def clear_jail(user_id: int, guild_id: int):
    get_player(user_id, guild_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET jail_until = 0 WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        conn.commit()


def is_jailed(user_id: int, guild_id: int) -> dict:
    player = get_player(user_id, guild_id)
    jail_until = player["jail_until"]
    now = int(time.time())

    if jail_until > now:
        return {"jailed": True, "seconds_remaining": jail_until - now}

    return {"jailed": False, "seconds_remaining": 0}


def set_heat(user_id: int, guild_id: int, value: int):
    get_player(user_id, guild_id)
    value = max(config.HEAT_MIN, min(config.HEAT_MAX, value))
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET heat = ? WHERE user_id = ? AND guild_id = ?",
            (value, user_id, guild_id),
        )
        conn.commit()


# =========================================================
# PLAYER: RIG LEVEL
# =========================================================

def set_rig_level(user_id: int, guild_id: int, rig_level: int):
    get_player(user_id, guild_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET rig_level = ? WHERE user_id = ? AND guild_id = ?",
            (rig_level, user_id, guild_id),
        )
        conn.commit()


# =========================================================
# LEADERBOARD
# =========================================================

def get_leaderboard(limit: int = 10, guild_id: int = None):
    with get_connection() as conn:
        if guild_id:
            rows = conn.execute(
                "SELECT * FROM players WHERE guild_id = ? ORDER BY bytes DESC LIMIT ?",
                (guild_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT user_id, SUM(bytes) as bytes, MAX(level) as level 
                   FROM players GROUP BY user_id ORDER BY bytes DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return rows


# =========================================================
# ADMIN / MAINTENANCE
# =========================================================

def reset_player(user_id: int, guild_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        conn.commit()


def get_economy_stats(guild_id: int = None) -> dict:
    with get_connection() as conn:
        if guild_id:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total_players,
                    COALESCE(SUM(bytes), 0) AS total_bytes,
                    COALESCE(AVG(level), 0) AS avg_level,
                    COALESCE(AVG(bytes), 0) AS avg_bytes
                FROM players WHERE guild_id = ?
            """, (guild_id,)).fetchone()
        else:
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
