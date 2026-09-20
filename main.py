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
from logger import get_logger

logger = get_logger(__name__)

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
# help_command=None menonaktifkan command help bawaan agar bisa kita buat versi custom.
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
    "cogs.admin",
    "cogs.help",
    "cogs.tasks",
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
            logger.info(f"Berhasil load cog: {extension}")
        except Exception as e:
            logger.error(f"Gagal load cog {extension}: {e}", exc_info=True)


@bot.event
async def on_ready():
    """
    Event ini otomatis terpanggil saat bot berhasil login dan siap dipakai.
    Berguna untuk konfirmasi di terminal bahwa koneksi ke Discord berhasil.
    """
    logger.info(f"Bot berhasil online sebagai: {bot.user}")
    logger.info(f"Terhubung ke {len(bot.guilds)} server")
    logger.info("CyberHeist Bot siap menerima command!")


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    """
    Command sederhana untuk tes koneksi/latency bot.
    Contoh pemakaian di Discord: !ping
    """
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency: {latency_ms}ms")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """
    Global error handler untuk semua command yang tidak punya
    error handler sendiri. Mencegah bot diam tanpa respons.
    """
    # Jika error sudah di-handle di level cog, skip
    if hasattr(ctx.command, "on_error"):
        return

    # Jika cog punya error handler sendiri, skip
    if ctx.cog and ctx.cog.has_error_handler():
        return

    # Handle error umum
    if isinstance(error, commands.CommandNotFound):
        # Jangan spam channel untuk command yang tidak ada
        return

    elif isinstance(error, commands.DisabledCommand):
        await ctx.send(f"❌ Command `!{ctx.command}` sedang dinonaktifkan.")

    elif isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send(f"❌ Command `!{ctx.command}` tidak bisa digunakan di DM.")
        except discord.Forbidden:
            pass

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Kamu tidak punya permission untuk menggunakan command ini.")

    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Bot tidak punya permission yang cukup untuk menjalankan command ini.")

    elif isinstance(error, commands.CommandOnCooldown):
        # Ini seharusnya sudah di-handle di masing-masing command
        # Tapi sebagai fallback:
        remaining = round(error.retry_after, 1)
        await ctx.send(f"⏳ Command ini masih cooldown. Tunggu **{remaining} detik** lagi.")

    else:
        # Error yang tidak terduga - log dan beri tahu user
        logger.error(f"Unhandled error in command {ctx.command}: {error}", exc_info=error)
        await ctx.send(
            f"❌ Terjadi error saat menjalankan command `!{ctx.command}`.\n"
            f"Error sudah dicatat. Jika terus terjadi, hubungi admin bot."
        )


# --- Jalankan Bot ---
if __name__ == "__main__":
    try:
        # Pastikan database & tabel 'players' sudah siap SEBELUM bot online.
        logger.info("Inisialisasi database...")
        database.init_db()
        logger.info("Database siap. Menjalankan bot...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Bot crash dengan error fatal: {e}", exc_info=True)