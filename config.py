"""
CyberHeist Bot - Game Configuration
=====================================
File ini berisi SEMUA angka balancing game (XP curve, harga rig, dll)
dipisah dari logic database/bot agar mudah di-tweak tanpa menyentuh
kode inti. Kalau nanti mau rebalance game, cukup edit file ini.
"""

# =========================================================
# XP & LEVELING
# =========================================================
# Formula: XP dibutuhkan untuk naik ke level berikutnya
#   xp_needed = XP_BASE * (current_level ** XP_EXPONENT)
#
# Dengan BASE=50, EXPONENT=1.5:
#   Level 1 -> 2   butuh ~50 XP
#   Level 5 -> 6   butuh ~559 XP
#   Level 10 -> 11 butuh ~1581 XP
#   Level 50 -> 51 butuh ~17677 XP
# Kurva ini landai di awal (biar terasa cepat naik level),
# lalu makin curam di level tinggi (long-term progression goal).
XP_BASE = 50
XP_EXPONENT = 1.5


def xp_required_for_level(level: int) -> int:
    """
    Menghitung berapa XP yang dibutuhkan untuk naik dari `level`
    ke `level + 1`.
    """
    return round(XP_BASE * (level ** XP_EXPONENT))


# =========================================================
# HEAT SYSTEM
# =========================================================
HEAT_MIN = 0
HEAT_MAX = 100

# Heat yang ditambahkan setiap kali sukses !hack
HEAT_GAIN_PER_HACK = 8

# Di atas threshold ini, mulai ada penalti (misal: naik risiko gagal/jail)
HEAT_DANGER_THRESHOLD = 70

# Heat yang dikurangi setiap kali !clean berhasil
HEAT_REDUCTION_PER_CLEAN = 25

# --- Penalti saat Heat mencapai 100 (arrested/gerebek) ---
# Persentase Bytes yang disita sebagai denda saat tertangkap.
HEAT_ARREST_FINE_PERCENTAGE = 0.35  # 35% dari total Bytes

# Denda minimum tetap dikenakan walau Bytes player sedikit,
# supaya penalti tetap terasa bahkan di awal game.
HEAT_ARREST_FINE_MINIMUM = 50

# Berapa lama (detik) player tidak bisa !hack setelah arrested.
# 300 detik = 5 menit.
JAIL_COOLDOWN_SECONDS = 300

# =========================================================
# CLEAN SYSTEM
# =========================================================
CLEAN_COOLDOWN_SECONDS = 180  # 3 menit
CLEAN_BASE_COST = 50
CLEAN_SCALING_FACTOR = 10


# =========================================================
# HARDWARE / RIG TIERS (untuk !shop dan !rig)
# =========================================================
# Placeholder awal - detail harga & income final akan kita
# sempurnakan nanti pas membangun sistem !shop secara spesifik.
# Struktur ini sengaja dibuat list of dict biar gampang ditambah
# tier baru tanpa mengubah logic kode.
RIG_TIERS = [
    {
        "tier": 1,
        "name": "Botnet Kecil",
        "price": 450,
        "income_per_tick": 5,   # Bytes yang dihasilkan tiap kali !net diklaim
    },
    {
        "tier": 2,
        "name": "GPU Rig",
        "price": 2500,
        "income_per_tick": 30,
    },
    {
        "tier": 3,
        "name": "Server Rack",
        "price": 10000,
        "income_per_tick": 150,
    },
]


# =========================================================
# DAILY REWARD SYSTEM
# =========================================================
# Base reward yang dijamin setiap hari
DAILY_BASE_BYTES_MIN = 100
DAILY_BASE_BYTES_MAX = 200

# Streak bonus (capped)
DAILY_STREAK_BONUS_PER_DAY = 10  # +10 Bytes per hari streak
DAILY_STREAK_BONUS_MAX = 100      # Maksimal bonus streak 100 Bytes

# Mystery bonus drops
DAILY_BONUS_EXTRA_BYTES_MIN = 25
DAILY_BONUS_EXTRA_BYTES_MAX = 50
DAILY_BONUS_XP_MIN = 20
DAILY_BONUS_XP_MAX = 40
DAILY_BONUS_HEAT_REDUCE_MIN = 10
DAILY_BONUS_HEAT_REDUCE_MAX = 20
DAILY_BONUS_CIPHER_BYTES_MIN = 15
DAILY_BONUS_CIPHER_BYTES_MAX = 30

# Anti-spam cooldown
DAILY_COOLDOWN_SECONDS = 10


# =========================================================
# DATABASE
# =========================================================
# Path absolut relatif ke lokasi file ini, bukan CWD
import os as _os
_BASE_DIR = _os.path.dirname(_os.path.abspath(__file__))
DATABASE_PATH = _os.path.join(_BASE_DIR, "data", "cyberheist.sqlite3")