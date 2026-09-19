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
        Menampilkan status player: Level, Bytes, XP, Heat, Rig, dan
        status Jail (kalau sedang dalam masa karantina setelah arrested).
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

        # --- CEK STATUS JAIL ---
        # Kalau player sedang dalam masa karantina (habis arrested),
        # tampilkan sebagai field tambahan yang mencolok di embed.
        jail_status = database.is_jailed(ctx.author.id)

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

        # Field status jail hanya muncul kalau player memang sedang jailed,
        # supaya embed tidak "berisik" untuk player yang statusnya normal.
        if jail_status["jailed"]:
            remaining = jail_status["seconds_remaining"]
            minutes, seconds = divmod(remaining, 60)
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

            embed.add_field(
                name="🔒 Status Karantina",
                value=(
                    f"**DALAM PENGAWASAN** - tidak bisa `!hack`\n"
                    f"Sisa waktu: **{time_str}**"
                ),
                inline=False,
            )
            # Ubah warna embed jadi merah kalau sedang jailed, biar langsung
            # kelihatan mencolok dari warna default ungu.
            embed.color = discord.Color.red()

        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """
    Fungsi wajib yang dipanggil discord.py saat cog ini di-load
    lewat bot.load_extension("cogs.profile").
    """
    await bot.add_cog(ProfileCog(bot))