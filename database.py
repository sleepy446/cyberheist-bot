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
    Juga menjalankan migration ringan untuk menambah kolom baru
    (jail_until) ke tabel yang sudah ada sebelumnya, tanpa menghapus
    data player yang sudah tersimpan.
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

        # --- Migration: tambah kolom jail_until kalau tabel lama belum punya ---
        # Ini penting karena tabel `players` di database kamu sudah ada isinya
        # (dibuat sebelum kolom ini ditambahkan). CREATE TABLE IF NOT EXISTS
        # di atas TIDAK akan menambah kolom baru ke tabel yang sudah ada,
        # jadi kita cek manual dan ALTER TABLE kalau perlu.
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
    Menggunakan 'with get_connection() as conn:' otomatis menutup
    koneksi setelah selesai, walaupun terjadi error di tengah jalan.
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # biar hasil query bisa diakses seperti dict
    try:
        yield conn
    finally:
        conn.close()


# =========================================================
# PLAYER: CREATE & READ
# =========================================================

def get_player(user_id: int) -> sqlite3.Row:
    """
    Mengambil data player berdasarkan user_id.
    Kalau player belum terdaftar di database, otomatis dibuatkan
    row baru dengan nilai default (bytes=0, level=1, dst).
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
    """
    Menambah (atau mengurangi jika amount negatif) jumlah Bytes player.
    Memastikan player sudah ada di database dulu (auto-create).
    """
    get_player(user_id)  # pastikan row sudah ada
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET bytes = bytes + ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.commit()


# =========================================================
# PLAYER: XP & LEVEL
# =========================================================

def add_xp(user_id: int, amount: int) -> dict:
    """
    Menambah XP player, dan otomatis menangani level-up jika XP
    yang terkumpul sudah melewati threshold (bisa naik lebih dari
    1 level sekaligus kalau XP yang didapat besar).

    Return dict berisi info untuk keperluan pesan di Discord:
        {
            "leveled_up": bool,
            "old_level": int,
            "new_level": int,
            "current_xp": int,
        }
    """
    player = get_player(user_id)
    current_level = player["level"]
    current_xp = player["xp"] + amount

    old_level = current_level
    leveled_up = False

    # Cek apakah XP sekarang cukup untuk naik level (bisa berkali-kali
    # kalau amount XP yang didapat sangat besar)
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


# =========================================================
# PLAYER: HEAT
# =========================================================

def add_heat(user_id: int, amount: int) -> dict:
    """
    Menambah (atau mengurangi jika amount negatif) Heat player,
    dengan clamp otomatis ke range [HEAT_MIN, HEAT_MAX].

    Jika Heat mencapai 100, player terkena penalti (gerebek/jail):
      - Heat di-reset ke 0
      - Bytes disita sebagian (HEAT_ARREST_FINE_PERCENTAGE dari total,
        minimal HEAT_ARREST_FINE_MINIMUM)
      - Player masuk status "jailed" selama JAIL_COOLDOWN_SECONDS detik
        (disimpan sebagai timestamp di kolom jail_until), sehingga
        tidak bisa !hack sampai cooldown ini berakhir.

    Return dict berisi informasi heat terbaru dan status penalti:
        {
            "heat": int,
            "arrested": bool,
            "fine": int,
            "jail_until": int   # unix timestamp, 0 kalau tidak arrested
        }
    """
    player = get_player(user_id)
    current_heat = player["heat"]
    new_heat = current_heat + amount

    arrested = False
    fine = 0
    jail_until = player["jail_until"]

    # Jika Heat menyentuh atau melewati batas maksimal (100)
    if new_heat >= config.HEAT_MAX:
        arrested = True
        new_heat = 0  # Reset heat setelah tertangkap

        # Penalti denda: sita persentase dari total Bytes player
        # (minimal HEAT_ARREST_FINE_MINIMUM Bytes kalau punya)
        current_bytes = player["bytes"]
        if current_bytes > 0:
            fine = max(
                config.HEAT_ARREST_FINE_MINIMUM,
                round(current_bytes * config.HEAT_ARREST_FINE_PERCENTAGE),
            )
            # Pastikan denda tidak melebihi bytes yang dimiliki
            fine = min(fine, current_bytes)

        # Set cooldown: player tidak bisa !hack sampai waktu ini
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
    """
    Membatalkan status jail player secara instan (set jail_until = 0).
    Dipakai oleh command admin !unjail untuk keperluan testing/moderasi,
    supaya tidak perlu edit database manual via GUI (yang rawan human
    error dan berisiko bikin file ter-lock saat bot sedang berjalan).
    """
    get_player(user_id)  # pastikan row sudah ada
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET jail_until = 0 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def is_jailed(user_id: int) -> dict:
    """
    Mengecek apakah player masih dalam status "jailed" (cooldown
    setelah arrested). Dipanggil oleh command seperti !hack SEBELUM
    mengizinkan aksi, supaya player tidak bisa hack selama masih
    dalam masa tahanan.

    Return dict:
        {
            "jailed": bool,
            "seconds_remaining": int   # 0 kalau tidak jailed
        }
    """
    player = get_player(user_id)
    jail_until = player["jail_until"]
    now = int(time.time())

    if jail_until > now:
        return {"jailed": True, "seconds_remaining": jail_until - now}

    return {"jailed": False, "seconds_remaining": 0}


# =========================================================
# PLAYER: RIG LEVEL
# =========================================================

def set_rig_level(user_id: int, rig_level: int):
    """Mengatur rig_level player ke nilai tertentu (dipakai saat beli upgrade)."""
    get_player(user_id)  # pastikan row sudah ada
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET rig_level = ? WHERE user_id = ?",
            (rig_level, user_id),
        )
        conn.commit()


# =========================================================
# LEADERBOARD
# =========================================================

def get_leaderboard(limit: int = 10):
    """
    Mengambil daftar top player berdasarkan Bytes terbanyak.
    Return list of sqlite3.Row, urutan dari terkaya ke termiskin.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM players ORDER BY bytes DESC LIMIT ?", (limit,)
        ).fetchall()
        return rows