"""
CyberHeist Bot - Clean / Heat Reduction Cog
===========================================
Cog ini menangani mekanisme manajemen risiko via command /clean.
Digunakan player untuk mencuci jejak digital / menurunkan Heat
dengan membayar sejumlah Bytes.
"""

import discord
from discord import app_commands
from discord.ext import commands

import database
import config


class CleanCog(commands.Cog):
    """Kumpulan command untuk membersihkan jejak / menurunkan Heat."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clean", description="Bersihkan jejak digital dan turunkan Heat dengan membayar Bytes")
    @app_commands.checks.cooldown(1, config.CLEAN_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def clean(self, interaction: discord.Interaction):
        """
        Menurunkan tingkat Heat (buronan) player.
        Pemakaian di Discord: /clean
        """
        user_id = interaction.user.id
        player = database.get_player(user_id)
        current_heat = player["heat"]

        if current_heat <= 0:
            await interaction.response.send_message(
                f"🛡️ {interaction.user.mention}, jejak digitalmu sudah bersih total! Heat kamu di angka `0/100`.",
                ephemeral=True
            )
            return

        # Biaya pembersihan: basis tetap + scaling berdasarkan level
        cleaning_cost = config.CLEAN_BASE_COST + (player["level"] * config.CLEAN_SCALING_FACTOR)

        if player["bytes"] < cleaning_cost:
            await interaction.response.send_message(
                f"❌ Bytes kamu tidak cukup untuk membayar jasa hacker VPN pembersih jejak!\n"
                f"Butuh **{cleaning_cost:,} Bytes** (Level player: {player['level']}). "
                f"Terus `/net` atau `/hack` dulu!",
                ephemeral=True
            )
            return

        # 1. Kurangi Bytes (bayar jasa)
        database.add_bytes(user_id, -cleaning_cost)

        # 2. Kurangi Heat sejumlah config
        heat_result = database.add_heat(user_id, -config.HEAT_REDUCTION_PER_CLEAN)
        new_heat = heat_result["heat"]

        if new_heat >= config.HEAT_DANGER_THRESHOLD:
            heat_status = "🚨 BAHAYA - Segera /clean!"
        elif new_heat >= config.HEAT_DANGER_THRESHOLD // 2:
            heat_status = "⚠️ Waspada"
        else:
            heat_status = "🟢 Aman"

        embed = discord.Embed(
            title="🧹 Jejak Digital Dibersihkan",
            description=f"Berhasil meretas balik server kepolisian virtual dan mencuci IP address, {interaction.user.mention}!",
            color=discord.Color.blue()
        )
        embed.add_field(name="💸 Biaya Jasa", value=f"-{cleaning_cost:,} Bytes", inline=True)
        embed.add_field(name="🔥 Penurunan Heat", value=f"-{config.HEAT_REDUCTION_PER_CLEAN} poin", inline=True)
        embed.add_field(name="🛡️ Heat Terbaru", value=f"`{new_heat}/100` - {heat_status}", inline=False)

        cooldown_minutes = config.CLEAN_COOLDOWN_SECONDS // 60
        embed.set_footer(text=f"Sistem pendinginan jejak aktif. Cooldown {cooldown_minutes} menit sebelum membersihkan lagi.")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog clean."""
    await bot.add_cog(CleanCog(bot))
