"""
CyberHeist Bot - Clean / Heat Reduction Cog
===========================================
Cog ini menangani mekanisme manajemen risiko via command !clean.
Digunakan player untuk mencuci jejak digital / menurunkan Heat
dengan membayar sejumlah Bytes atau menggunakan cooldown tertentu.
"""

import discord
from discord.ext import commands

import database
import config


class CleanCog(commands.Cog):
    """Kumpulan command untuk membersihkan jejak / menurunkan Heat."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clean", aliases=["wash", "laylow"])
    @commands.cooldown(1, 60, commands.BucketType.user)  # Cooldown 1 menit per pembersihan
    async def clean(self, ctx: commands.Context):
        """
        Menurunkan tingkat Heat (buronan) player.
        Pemakaian di Discord: !clean
        """
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        player = database.get_player(user_id, guild_id)
        current_heat = player["heat"]

        # Kalau heat sudah 0, tidak perlu dibersihkan
        if current_heat <= 0:
            # Penting: Reset cooldown jika aksi tidak jadi dilakukan
            ctx.command.reset_cooldown(ctx)
            await ctx.send(f"🛡️ {ctx.author.mention}, jejak digitalmu sudah bersih total! Heat kamu di angka `0/100`.")
            return

        # Tentukan biaya pembersihan berdasarkan seberapa tinggi heat saat ini
        # Contoh: Heat 50 = 100 Bytes (dihitung dari config atau rumus dinamis)
        cleaning_cost = current_heat * 3.5 

        if player["bytes"] < cleaning_cost:
            # Penting: Reset cooldown jika gagal bayar
            ctx.command.reset_cooldown(ctx)
            await ctx.send(
                f"❌ Bytes kamu tidak cukup untuk membayar jasa hacker VPN pembersih jejak!\n"
                f"Butuh **{cleaning_cost:,} Bytes** (Heat kamu saat ini: `{current_heat}/100`). "
                f"Terus `!net` atau `!hack` dulu!"
            )
            return

        # 1. Kurangi Bytes (bayar jasa)
        database.add_bytes(user_id, guild_id, -cleaning_cost)
        
        # 2. Kurangi Heat sejumlah config.
        # PERBAIKAN: Tangkap hasil dictionary dari database, lalu ambil nilai int ["heat"]-nya.
        heat_result = database.add_heat(user_id, guild_id, -config.HEAT_REDUCTION_PER_CLEAN)
        new_heat = heat_result["heat"]

        # Tentukan status Heat secara dinamis sesuai threshold config
        if new_heat >= config.HEAT_DANGER_THRESHOLD:
            heat_status = "🚨 BAHAYA - Segera !clean!"
        elif new_heat >= config.HEAT_DANGER_THRESHOLD // 2:
            heat_status = "⚠️ Waspada"
        else:
            heat_status = "🟢 Aman"

        # Susun Embed Respon
        embed = discord.Embed(
            title="🧹 Jejak Digital Dibersihkan",
            description=f"Berhasil meretas balik server kepolisian virtual dan mencuci IP address, {ctx.author.mention}!",
            color=discord.Color.blue()
        )
        embed.add_field(name="💸 Biaya Jasa", value=f"-{cleaning_cost:,} Bytes", inline=True)
        embed.add_field(name="🔥 Penurunan Heat", value=f"-{config.HEAT_REDUCTION_PER_CLEAN} poin", inline=True)
        embed.add_field(name="🛡️ Heat Terbaru", value=f"`{new_heat}/100` - {heat_status}", inline=False)
        embed.set_footer(text="Sistem pendinginan jejak aktif. Cooldown 1 menit sebelum membersihkan lagi.")

        await ctx.send(embed=embed)

    @clean.error
    async def clean_error(self, ctx: commands.Context, error):
        """Menangani error cooldown command !clean."""
        if isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after, 1)
            await ctx.send(
                f"⏳ Proxy pembersih masih sibuk... Tunggu **{remaining} detik** lagi sebelum bisa `!clean`.",
                delete_after=5
            )
        else:
            # Print error lain ke console untuk debugging
            raise error


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog clean."""
    await bot.add_cog(CleanCog(bot))