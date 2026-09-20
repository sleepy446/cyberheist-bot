"""
CyberHeist Bot - Database Layer
==================================
File ini adalah satu-satunya tempat yang berurusan langsung dengan SQLite.
Semua cogs (hack, shop, profile, dll) akan memanggil fungsi-fungsi di
file ini, TIDAK PERNAH menulis query SQL mentah di file lain.
Tujuannya: kalau nanti kita ganti struktur tabel, cukup ubah di sini.

CATATAN DESAIN: Data player bersifat GLOBAL (satu wallet per user_id),
BUKAN per-server Discord. Artinya seorang player bisa main CyberHeist
dari server mana saja dan progressnya tetap sama/nyambung.
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
    Membuat folder data/ (kalau belum ada) dan tabel `players`
    (kalau belum ada). Dipanggil sekali saat bot pertama kali start.
    Juga menjalankan migration otomatis untuk 2 skenario:
      1. Tabel lama belum punya kolom jail_until -> ditambahkan.
      2. Tabel lama masih pakai skema guild_id (composite key) dari
         eksperimen multi-server yang sudah dibatalkan -> data digabung
         kembali jadi satu wallet global per user_id, kolom guild_id dibuang.
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

        # --- Migration 1: buang guild_id (dari eksperimen multi-server) ---
        # Kalau tabel yang sudah ada masih punya kolom guild_id, artinya ini
        # peninggalan skema lama. Kita gabungkan data per user_id (ambil
        # total Bytes gabungan, dan nilai TERBAIK untuk level/xp/heat/rig,
        # supaya progress testing tidak hilang), lalu buat ulang tabel
        # tanpa guild_id.
        if "guild_id" in existing_columns:
            logger.info("Migration: menghapus skema guild_id, menyatukan data player jadi wallet global...")
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
            logger.info("Migration guild_id selesai. Data player sekarang global per user_id.")

        # --- Migration 2: tambah kolom jail_until kalau tabel sangat lama belum punya ---
        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]
        if "jail_until" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN jail_until INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: kolom 'jail_until' berhasil ditambahkan.")

        # --- Migration 3: tambah kolom daily reward (last_daily_claim, daily_streak) ---
        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]
        if "last_daily_claim" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN last_daily_claim INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: kolom 'last_daily_claim' berhasil ditambahkan.")

        if "daily_streak" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN daily_streak INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration: kolom 'daily_streak' berhasil ditambahkan.")

    logger.info("Database siap. Tabel 'players' sudah ada/dibuat.")


@contextmanager
def get_connection():
    """
    Context manager untuk membuka koneksi SQLite dengan aman.
    timeout=10 membuat SQLite otomatis menunggu (retry) sampai 10 detik
    kalau file sedang dipakai proses lain, alih-alih langsung error
    'database is locked'. WAL mode memungkinkan baca/tulis bersamaan
    dengan lebih toleran, cocok untuk bot Discord dengan banyak command
    berjalan nyaris bersamaan dari berbagai user.
    """
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

def get_player(user_id: int) -> sqlite3.Row:
    """
    Mengambil data player berdasarkan user_id (global, lintas server).
    Kalau player belum terdaftar, otomatis dibuatkan row baru dengan
    nilai default. Thread-safe dengan INSERT OR IGNORE.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row is None:
            # INSERT OR IGNORE mencegah error jika thread lain sudah insert duluan
            conn.execute(
                "INSERT OR IGNORE INTO players (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM players WHERE user_id = ?", (user_id,)
            ).fetchone()

        return row


# =========================================================
# PLAYER: BYTES (currency)
# =========================================================

def add_bytes(user_id: int, amount: int):
    """
    Menambah (atau mengurangi jika amount negatif) jumlah Bytes player.
    PENTING: Bytes tidak akan pernah menjadi negatif (clamped ke 0).
    """
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = MAX(0, bytes + ?) WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


def set_bytes(user_id: int, amount: int):
    """Mengatur Bytes player LANGSUNG ke nilai tertentu (bukan menambah)."""
    get_player(user_id)
    amount = max(0, amount)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


# =========================================================
# PLAYER: XP & LEVEL
# =========================================================

def add_xp(user_id: int, amount: int) -> dict:
    """
    Menambah XP player, otomatis memproses level-up (bisa lebih dari
    1 level sekaligus). Return dict info untuk pesan Discord.
    """
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
    """Mengatur Level dan XP player LANGSUNG ke nilai tertentu."""
    get_player(user_id)
    level = max(1, level)
    xp = max(0, xp)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET level = ?, xp = ? WHERE user_id = ?",
            (level, xp, user_id),
        )
        conn.commit()


# =========================================================
# PLAYER: HEAT
# =========================================================

def add_heat(user_id: int, amount: int) -> dict:
    """
    Menambah/mengurangi Heat player dengan clamp [0, 100].
    Jika Heat mencapai 100 (dan amount POSITIF/penambahan): reset ke 0,
    sita denda (HEAT_ARREST_FINE_PERCENTAGE dari total Bytes, minimal
    HEAT_ARREST_FINE_MINIMUM), dan set jail_until (timestamp) selama
    JAIL_COOLDOWN_SECONDS ke depan.

    PENTING: Arrest HANYA terjadi saat penambahan heat (amount > 0) yang
    menyebabkan heat >= 100. Pengurangan heat (amount < 0) tidak akan
    trigger arrest walau nilainya sempat >= 100.
    """
    player = get_player(user_id)
    current_heat = player["heat"]
    new_heat = current_heat + amount

    arrested = False
    fine = 0
    jail_until = player["jail_until"]

    # Arrest HANYA jika: (1) heat increase (amount > 0), DAN (2) mencapai/lewati 100
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
            # Gunakan MAX(0, bytes - fine) untuk cegah bytes negatif
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
    """Membatalkan status jail player secara instan (set jail_until = 0)."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET jail_until = 0 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def is_jailed(user_id: int) -> dict:
    """
    Mengecek apakah player masih dalam status jail (cooldown setelah
    arrested). Dipanggil !hack SEBELUM mengizinkan aksi.
    """
    player = get_player(user_id)
    jail_until = player["jail_until"]
    now = int(time.time())

    if jail_until > now:
        return {"jailed": True, "seconds_remaining": jail_until - now}

    return {"jailed": False, "seconds_remaining": 0}


def set_heat(user_id: int, value: int):
    """Mengatur Heat player LANGSUNG (0-100), TANPA memicu logic jail."""
    get_player(user_id)
    value = max(config.HEAT_MIN, min(config.HEAT_MAX, value))
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET heat = ? WHERE user_id = ?",
            (value, user_id),
        )
        conn.commit()


# =========================================================
# PLAYER: RIG LEVEL
# =========================================================

def set_rig_level(user_id: int, rig_level: int):
    """Mengatur rig_level player ke nilai tertentu (dipakai saat beli upgrade)."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET rig_level = ? WHERE user_id = ?",
            (rig_level, user_id),
        )
        conn.commit()


def get_players_with_heat() -> list:
    """Mengambil semua player yang memiliki Heat > 0 untuk proses decay."""
    with get_connection() as conn:
        return conn.execute("SELECT user_id, heat FROM players WHERE heat > 0").fetchall()

def get_leaderboard(limit: int = 10):
    """
    Mengambil daftar top player berdasarkan Bytes terbanyak (global,
    tidak per-server, karena wallet player memang bersifat global).
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM players ORDER BY bytes DESC LIMIT ?", (limit,)
        ).fetchall()
        return rows


# =========================================================
# ADMIN / MAINTENANCE
# =========================================================

def reset_player(user_id: int):
    """Menghapus SELURUH data player (kembali ke kondisi seolah baru main)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
        conn.commit()


def get_economy_stats() -> dict:
    """Ringkasan statistik ekonomi: total player, total Bytes, rata-rata level & Bytes."""
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


# =========================================================
# DAILY REWARD SYSTEM
# =========================================================

def get_daily_status(user_id: int) -> dict:
    """
    Mengecek status daily reward player: apakah bisa klaim hari ini,
    streak saat ini, dan sisa waktu menuju reset UTC berikutnya.
    """
    player = get_player(user_id)
    current_day = int(time.time()) // 86400
    last_claim_day = player["last_daily_claim"]
    current_streak = player["daily_streak"]

    can_claim = last_claim_day < current_day
    is_streak_continued = (last_claim_day == current_day - 1)
    next_streak = (current_streak + 1) if is_streak_continued else 1

    # Hitung sisa detik menuju reset UTC (00:00 UTC berikutnya)
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
    Melakukan klaim daily reward secara atomic. Mengembalikan dict dengan
    status sukses/gagal dan detail reward yang diberikan.

    bonus_type: "extra_bytes", "xp", "heat", "cipher"
    bonus_value: nilai bonus sesuai tipe
    """
    get_player(user_id)
    current_day = int(time.time()) // 86400

    with get_connection() as conn:
        # Hitung streak baru
        daily_status = get_daily_status(user_id)
        if not daily_status["can_claim"]:
            return {"success": False, "reason": "already_claimed"}

        new_streak = daily_status["next_streak"]

        # Hitung total bytes yang akan ditambahkan
        total_bytes_gain = base_bytes + streak_bonus

        # Tambahkan bonus bytes jika tipe adalah extra_bytes atau cipher
        if bonus_type in ["extra_bytes", "cipher"]:
            total_bytes_gain += bonus_value

        # Atomic update dengan conditional WHERE
        cursor = conn.execute(
            """UPDATE players
               SET last_daily_claim = ?,
                   daily_streak = ?,
                   bytes = bytes + ?
               WHERE user_id = ? AND last_daily_claim < ?""",
            (current_day, new_streak, total_bytes_gain, user_id, current_day)
        )

        if cursor.rowcount == 0:
            # Race condition: player lain sudah claim duluan
            return {"success": False, "reason": "already_claimed"}

        conn.commit()

    # Proses bonus XP atau Heat reduction di luar transaksi atomic bytes
    # (karena fungsi ini punya transaksi sendiri yang aman)
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
    """Reset last_daily_claim ke 0 untuk testing (admin only)."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET last_daily_claim = 0 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()


def admin_set_streak(user_id: int, streak: int):
    """Set daily_streak ke nilai tertentu (admin only)."""
    get_player(user_id)
    streak = max(0, min(999999, streak))  # Bounds check
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET daily_streak = ? WHERE user_id = ?",
            (streak, user_id)
        )
        conn.commit()