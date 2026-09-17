"""
CyberHeist Bot - Entry Point
==============================
Ini adalah file utama (entry point) yang menjalankan bot Discord.
Versi ini masih tahap dasar: hanya untuk memastikan bot bisa online
dan merespons command sederhana (!ping) sebelum kita bangun sistem
database & command inti (hack, rig, clean, dll) di tahap berikutnya.
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

import database

# --- Load token dari file .env ---
# Kita simpan token di .env (bukan hardcode di kode) demi keamanan.
# .env sudah masuk .gitignore, jadi tidak akan ke-push ke GitHub.
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise ValueError(
        "DISCORD_TOKEN tidak ditemukan! Pastikan file .env sudah diisi "
        "dengan format: DISCORD_TOKEN=token_kamu"
    )

# --- Setup Intents ---
# Intents menentukan jenis data/event apa saja yang bot boleh terima dari Discord.
# message_content WAJIB aktif agar bot bisa membaca isi pesan (untuk command !hack, dll).
intents = discord.Intents.default()
intents.message_content = True

# --- Inisialisasi Bot ---
# command_prefix="!" sesuai rancangan GDD kita (semua command diawali tanda seru).
bot = commands.Bot(command_prefix="!", intents=intents)

# Daftar cog yang akan di-load otomatis saat bot start.
# Format: "cogs.<nama_file_tanpa_.py>"
# Cukup tambahkan nama file di list ini setiap kali kita bikin cog baru,
# tidak perlu ubah logic loading-nya.
INITIAL_EXTENSIONS = [
    "cogs.profile",
    "cogs.hack",
    "cogs.shop",
    "cogs.net",
    "cogs.clean",
]


@bot.event
async def setup_hook():
    """
    Dipanggil otomatis oleh discord.py SEBELUM bot login ke Discord.
    Tempat yang tepat untuk load semua cogs/extensions.
    """
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            print(f"[COG] Berhasil load: {extension}")
        except Exception as e:
            print(f"[COG ERROR] Gagal load {extension}: {e}")


@bot.event
async def on_ready():
    """
    Event ini otomatis terpanggil saat bot berhasil login dan siap dipakai.
    Berguna untuk konfirmasi di terminal bahwa koneksi ke Discord berhasil.
    """
    print(f"[OK] Bot berhasil online sebagai: {bot.user}")
    print(f"[OK] Terhubung ke {len(bot.guilds)} server.")
    print("[OK] CyberHeist Bot siap menerima command...")


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """
    Command sederhana untuk tes koneksi/latency bot.
    Contoh pemakaian di Discord: !ping
    """
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency_ms}ms")


# --- Jalankan Bot ---
if __name__ == "__main__":
    # Pastikan database & tabel 'players' sudah siap SEBELUM bot online.
    database.init_db()
    bot.run(TOKEN)