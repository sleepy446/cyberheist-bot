"""
CyberHeist Bot - Net / Passive Income Cog
==========================================
Cog ini menangani klaim hasil tambang/passive income (/net)
berdasarkan level hardware (rig) yang dimiliki player.
"""

import discord
from discord import app_commands
from discord.ext import commands

import database
import config


class NetCog(commands.Cog):
    """Kumpulan command untuk klaim passive income dari hardware."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="net", description="Klaim hasil passive income dari hardware mining aktif")
    @app_commands.checks.cooldown(1, 300, key=lambda i: i.user.id)  # Cooldown 5 menit
    async def net(self, interaction: discord.Interaction):
        """
        Klaim hasil passive income dari rig/hardware yang aktif.
        Pemakaian di Discord: /net
        """
        user_id = interaction.user.id
        player = database.get_player(user_id)
        rig_level = player["rig_level"]

        if rig_level == 0:
            await interaction.response.send_message(
                f"⚠️ {interaction.user.mention}, kamu belum punya hardware/rig penambangan!\n"
                f"Beli dulu rig pertamamu pakai command `/shop` atau `/buy 1`.",
                ephemeral=True
            )
            return

        rig_data = config.RIG_TIERS[rig_level - 1]
        income = rig_data["income_per_tick"]
        rig_name = rig_data["name"]

        database.add_bytes(user_id, income)

        embed = discord.Embed(
            title="📡 Jaringan Penambangan Berhasil Diklaim",
            description=f"Berhasil menyedot hasil tambang dari **{rig_name}**!",
            color=discord.Color.teal()
        )
        embed.add_field(name="⚙️ Hardware Aktif", value=f"`{rig_name}` (Tier {rig_level})", inline=False)
        embed.add_field(name="💰 Bytes Didapat", value=f"+{income:,} Bytes", inline=True)
        embed.set_footer(text="Klaim ulang setelah cooldown habis untuk hasil berikutnya.")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog net."""
    await bot.add_cog(NetCog(bot))
