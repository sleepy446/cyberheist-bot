"""
CyberHeist Bot - Help Cog
=========================
Cog ini menangani command /help (Slash Command) untuk player
dan !ahelp (Prefix Command) untuk Admin/Owner.
Juga menyediakan slash command /ping untuk latency check.
"""

import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):
    """Kumpulan command bantuan dan informasi sistem."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_admin_command(self, cmd: commands.Command) -> bool:
        """
        Mengecek apakah command adalah admin command.
        Cek: (1) command ada di AdminCog, atau (2) punya @commands.is_owner() check.
        """
        if cmd.cog and cmd.cog.__class__.__name__ == "AdminCog":
            return True

        for check in cmd.checks:
            check_name = getattr(check, "__qualname__", "")
            if "is_owner" in check_name:
                return True

        return False

    @app_commands.command(name="ping", description="Cek latensi koneksi bot ke Discord")
    async def ping(self, interaction: discord.Interaction):
        """Slash command sederhana untuk memeriksa latency bot."""
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Latency: **{latency_ms}ms**")

    @app_commands.command(name="help", description="Tampilkan daftar semua slash commands untuk pemain")
    async def help_player(self, interaction: discord.Interaction):
        """Menampilkan daftar slash commands yang tersedia untuk player."""
        embed = discord.Embed(
            title="🕵️ CyberHeist - Player Slash Commands",
            description="Semua player commands sekarang menggunakan **Slash Commands** (`/`):\n",
            color=discord.Color.green()
        )

        # Daftar command slash player yang terdaftar
        player_commands = [
            ("`/hack`", "Hack target acak untuk mendapatkan Bytes dan XP (Cooldown: 4 detik)"),
            ("`/profile`", "Lihat profil, statistik hacker, level, Bytes, Heat, hardware, dan streak"),
            ("`/leaderboard`", "Tampilkan peringkat 10 hacker terkaya di seluruh server"),
            ("`/shop`", "Lihat hardware penambangan siber yang tersedia di Black Market"),
            ("`/buy <tier>`", "Beli hardware rig dengan fitur autocomplete pilihan"),
            ("`/net`", "Klaim passive income dari hardware aktif (Cooldown: 5 menit)"),
            ("`/clean`", "Bersihkan jejak digital dan turunkan Heat dengan membayar Bytes"),
            ("`/daily`", "Klaim hadiah harian, bonus streak, dan mystery drop (Reset 00:00 UTC)"),
            ("`/ping`", "Cek latensi koneksi bot ke server Discord"),
            ("`/help`", "Tampilkan panduan dan daftar perintah ini"),
        ]

        for name, desc in player_commands:
            embed.add_field(name=name, value=f"└─ {desc}", inline=False)

        embed.set_footer(text="Ketik / lalu pilih command untuk mulai bermain CyberHeist!")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="ahelp")
    @commands.is_owner()
    async def help_admin(self, ctx: commands.Context):
        """Menampilkan daftar command untuk admin (Prefix !)."""
        embed = discord.Embed(
            title="🔧 CyberHeist - Admin Commands (Prefix !)",
            description="Daftar command khusus Admin/Owner (tetap menggunakan prefix `!`):\n",
            color=discord.Color.red()
        )

        admin_commands = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            if self._is_admin_command(cmd):
                aliases = f" (alias: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                description = cmd.help or "Tidak ada deskripsi."
                admin_commands.append(f"**!{cmd.name}**{aliases}\n└─ {description}")

        if admin_commands:
            embed.description += "\n\n".join(admin_commands)
        else:
            embed.description += "\nTidak ada admin command yang tersedia."

        embed.set_footer(text="Command ini hanya bisa digunakan oleh Owner bot.")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog help."""
    await bot.add_cog(HelpCog(bot))
