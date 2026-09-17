"""
CyberHeist Bot - Profile Cog
==============================
Cog ini menangani command yang berkaitan dengan menampilkan status
player: !profile dan !stats (alias). Sifatnya read-only terhadap
database, jadi jadi tempat yang aman untuk validasi awal integrasi
Cogs + database layer.
"""

import discord
from discord.ext import commands

import database
import config


class ProfileCog(commands.Cog):
    """Kumpulan command untuk menampilkan status/profil player."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["stats"])
    async def profile(self, ctx: commands.Context):
        """
        Menampilkan status player: Level, Bytes, XP, Heat, dan Rig.
        Pemakaian di Discord: !profile atau !stats
        """
        player = database.get_player(ctx.author.id)

        # Hitung XP yang dibutuhkan untuk naik ke level berikutnya,
        # supaya bisa ditampilkan sebagai progress bar sederhana (xp/xp_needed)
        xp_needed = config.xp_required_for_level(player["level"])

        # Tentukan status Heat secara deskriptif, bukan cuma angka mentah,
        # biar player langsung paham seberapa bahaya kondisinya saat ini.
        heat = player["heat"]
        if heat >= config.HEAT_DANGER_THRESHOLD:
            heat_status = "🔴 BAHAYA - Segera !clean!"
        elif heat >= config.HEAT_DANGER_THRESHOLD // 2:
            heat_status = "🟡 Waspada"
        else:
            heat_status = "🟢 Aman"

        # Cari nama rig sesuai rig_level player (rig_level 0 = belum punya hardware)
        if player["rig_level"] == 0:
            rig_name = "Belum ada hardware"
        else:
            # rig_level 1 -> index 0 di RIG_TIERS, dst.
            rig_name = config.RIG_TIERS[player["rig_level"] - 1]["name"]

        embed = discord.Embed(
            title=f"🕵️ Profil Hacker: {ctx.author.display_name}",
            color=discord.Color.dark_purple(),
        )
        embed.add_field(name="Level", value=f"`{player['level']}`", inline=True)
        embed.add_field(
            name="XP", value=f"`{player['xp']} / {xp_needed}`", inline=True
        )
        embed.add_field(name="Bytes", value=f"`{player['bytes']:,}`", inline=True)
        embed.add_field(
            name="Heat", value=f"`{heat}/100` - {heat_status}", inline=False
        )
        embed.add_field(name="Hardware", value=f"`{rig_name}`", inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """
    Fungsi wajib yang dipanggil discord.py saat cog ini di-load
    lewat bot.load_extension("cogs.profile").
    """
    await bot.add_cog(ProfileCog(bot))