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
        "price": 500,
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
# DATABASE
# =========================================================
DATABASE_PATH = "data/cyberheist.sqlite3"