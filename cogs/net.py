"""
CyberHeist Bot - Net / Passive Income Cog
==========================================
Cog ini menangani klaim hasil tambang/passive income (!net)
berdasarkan level hardware (rig) yang dimiliki player.
Dilengkapi cooldown agar player harus menunggu waktu tertentu untuk klaim lagi.
"""

import discord
from discord.ext import commands

import database
import config


class NetCog(commands.Cog):
    """Kumpulan command untuk klaim passive income dari hardware."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="net", aliases=["mine", "claim"])
    @commands.cooldown(1, 300, commands.BucketType.user)  # Cooldown 5 menit (bisa disesuaikan nanti)
    async def net(self, ctx: commands.Context):
        """
        Klaim hasil passive income dari rig/hardware yang aktif.
        Pemakaian di Discord: !net
        """
        user_id = ctx.author.id
        player = database.get_player(user_id)
        rig_level = player["rig_level"]

        # Cek apakah player sudah punya hardware (rig_level > 0)
        if rig_level == 0:
            # Karena command gagal, kita reset cooldown-nya biar player gak rugi
            ctx.command.reset_cooldown(ctx)
            await ctx.send(
                f"⚠️ {ctx.author.mention}, kamu belum punya hardware/rig penambangan!\n"
                f"Beli dulu rig pertamamu pakai command `!shop` atau `!buy 1`."
            )
            return

        # Ambil data income berdasarkan rig_level di config.py
        # rig_level 1 ada di index 0 RIG_TIERS
        rig_data = config.RIG_TIERS[rig_level - 1]
        income = rig_data["income_per_tick"]
        rig_name = rig_data["name"]

        # Tambahkan Bytes ke database player
        database.add_bytes(user_id, income)

        embed = discord.Embed(
            title="📡 Jaringan Penambangan Berhasil Diklaim",
            description=f"Berhasil menyedot hasil tambang dari **{rig_name}**!",
            color=discord.Color.teal()
        )
        embed.add_field(name="⚙️ Hardware Aktif", value=f"`{rig_name}` (Tier {rig_level})", inline=False)
        embed.add_field(name="💰 Bytes Didapat", value=f"+{income:,} Bytes", inline=True)
        embed.set_footer(text="Klaim ulang setelah cooldown habis untuk hasil berikutnya.")

        await ctx.send(embed=embed)

    @net.error
    async def net_error(self, ctx: commands.Context, error):
        """Menangani error cooldown command !net."""
        if isinstance(error, commands.CommandOnCooldown):
            remaining_minutes = round(error.retry_after / 60, 1)
            await ctx.send(
                f"⏳ Sistem jaringan masih dalam enkripsi ulang... "
                f"Tunggu **{remaining_minutes} menit** lagi sebelum bisa `!net` kembali.",
                delete_after=6
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog net."""
    await bot.add_cog(NetCog(bot))