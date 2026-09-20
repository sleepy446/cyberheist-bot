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
                user_id     INTEGER PRIMARY KEY,
                bytes       INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                heat        INTEGER NOT NULL DEFAULT 0,
                rig_level   INTEGER NOT NULL DEFAULT 0,
                jail_until  INTEGER NOT NULL DEFAULT 0
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
            print("[DB] Migration: menghapus skema guild_id, menyatukan data player jadi wallet global...")
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
            print("[DB] Migration guild_id selesai. Data player sekarang global per user_id.")

        # --- Migration 2: tambah kolom jail_until kalau tabel sangat lama belum punya ---
        existing_columns = [
            row["name"] for row in conn.execute("PRAGMA table_info(players)")
        ]
        if "jail_until" not in existing_columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN jail_until INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
            print("[DB] Migration: kolom 'jail_until' berhasil ditambahkan.")

    print("[DB] Database siap. Tabel 'players' sudah ada/dibuat.")


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
    nilai default.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO players (user_id) VALUES (?)", (user_id,)
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
    """Menambah (atau mengurangi jika amount negatif) jumlah Bytes player."""
    get_player(user_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = bytes + ? WHERE user_id = ?",
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
    Jika Heat mencapai 100: reset ke 0, sita denda (HEAT_ARREST_FINE_PERCENTAGE
    dari total Bytes, minimal HEAT_ARREST_FINE_MINIMUM), dan set jail_until
    (timestamp) selama JAIL_COOLDOWN_SECONDS ke depan.
    """
    player = get_player(user_id)
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