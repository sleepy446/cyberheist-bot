"""
CyberHeist Bot - Admin/Owner Cog
===================================
Cog ini berisi command-command khusus untuk keperluan development,
testing, dan moderasi. HANYA bisa dijalankan oleh Owner bot (akun
yang membuat Discord Application-nya), memakai @commands.is_owner().

Ini jauh lebih aman dan cepat dibanding edit database.sqlite3 manual
lewat GUI (seperti DB Browser), yang selain rawan salah ketik, juga
berisiko bikin file database ter-lock kalau dibuka bersamaan saat
bot sedang jalan.
"""

import discord
from discord.ext import commands

import database


class AdminCog(commands.Cog):
    """Kumpulan command khusus owner bot untuk testing & moderasi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="unjail", aliases=["pardon", "bebas"])
    @commands.is_owner()
    async def unjail(self, ctx: commands.Context, member: discord.Member = None):
        """
        Membatalkan status jail seorang player secara instan.
        HANYA bisa dipakai oleh Owner bot.

        Pemakaian di Discord:
          !unjail          -> membebaskan diri sendiri
          !unjail @user    -> membebaskan player lain (misal buat testing)
        """
        # Kalau tidak menyebut siapa-siapa, target-nya diri sendiri
        target = member or ctx.author

        jail_status_before = database.is_jailed(target.id)

        if not jail_status_before["jailed"]:
            await ctx.send(f"ℹ️ {target.mention} sedang tidak dalam status jail, tidak ada yang perlu dibebaskan.")
            return

        database.clear_jail(target.id)

        embed = discord.Embed(
            title="🔓 Status Jail Dibatalkan (Admin Override)",
            description=f"{target.mention} sekarang bebas dan bisa `!hack` lagi.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Dieksekusi oleh: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @unjail.error
    async def unjail_error(self, ctx: commands.Context, error):
        """Menangani error command !unjail (terutama kalau bukan owner)."""
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Command ini cuma bisa dipakai oleh Owner bot.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member tidak ditemukan. Pastikan mention/nama user-nya benar.")
        else:
            raise error


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog admin."""
    await bot.add_cog(AdminCog(bot))