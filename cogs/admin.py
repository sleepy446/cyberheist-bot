"""
CyberHeist Bot - Admin/Owner Cog
===================================
Cog ini berisi command-command khusus untuk keperluan development,
testing, dan moderasi. SEMUA command di sini HANYA bisa dijalankan
oleh Owner bot (akun yang membuat Discord Application-nya), memakai
@commands.is_owner().

Ini jauh lebih aman dan cepat dibanding edit database.sqlite3 manual
lewat GUI (seperti DB Browser), yang selain rawan salah ketik, juga
berisiko bikin file database ter-lock kalau dibuka bersamaan saat
bot sedang jalan.

Daftar command:
  !unjail    <@user>            - Batalkan status jail instan
  !addbytes  <@user> <amount>   - Tambah/kurangi Bytes (bisa negatif)
  !setbytes  <@user> <amount>   - Set Bytes langsung ke angka tertentu
  !addxp     <@user> <amount>   - Tambah XP (otomatis proses level up)
  !setlevel  <@user> <level>    - Set Level langsung (reset XP ke 0)
  !setheat   <@user> <0-100>    - Set Heat langsung tanpa trigger jail
  !setrig    <@user> <tier>     - Set rig_level langsung
  !resetplayer <@user> confirm  - Hapus semua data player (perlu konfirmasi)
  !playerinfo <@user>           - Lihat SEMUA raw data player (debug view)
  !dbstats                      - Statistik ekonomi keseluruhan server
  !reload    <nama_cog>         - Hot-reload satu cog tanpa restart bot
"""

import time

import discord
from discord.ext import commands

import database
import config


class AdminCog(commands.Cog):
    """Kumpulan command khusus owner bot untuk testing & moderasi."""

    # Contoh pemakaian tiap command, dipakai oleh error handler di bawah
    # supaya pesan error selalu kasih contoh yang jelas dan konsisten,
    # bukan cuma bilang "argumen kurang" tanpa tahu format yang benar.
    # Kalau nambah command baru, tambahkan juga entry-nya di sini.
    COMMAND_EXAMPLES = {
        "unjail": "!unjail [@user]",
        "addbytes": "!addbytes @user 500",
        "setbytes": "!setbytes @user 10000",
        "addxp": "!addxp @user 1000",
        "setlevel": "!setlevel @user 50",
        "setheat": "!setheat @user 65",
        "setrig": "!setrig @user 2",
        "resetplayer": "!resetplayer @user confirm",
        "playerinfo": "!playerinfo [@user]",
        "dbstats": "!dbstats",
        "reload": "!reload hack",
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =====================================================
    # JAIL OVERRIDE
    # =====================================================

    @commands.command(name="unjail", aliases=["pardon", "bebas"])
    @commands.is_owner()
    async def unjail(self, ctx: commands.Context, member: discord.Member = None):
        """
        Membatalkan status jail seorang player secara instan.
        Pemakaian: !unjail [@user]  (default: diri sendiri)
        """
        target = member or ctx.author
        jail_status = database.is_jailed(target.id)

        if not jail_status["jailed"]:
            await ctx.send(f"ℹ️ {target.mention} sedang tidak dalam status jail.")
            return

        database.clear_jail(target.id)
        embed = discord.Embed(
            title="🔓 Status Jail Dibatalkan (Admin Override)",
            description=f"{target.mention} sekarang bebas dan bisa `!hack` lagi.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Dieksekusi oleh: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # =====================================================
    # BYTES OVERRIDE
    # =====================================================

    @commands.command(name="addbytes", aliases=["givebytes"])
    @commands.is_owner()
    async def addbytes(self, ctx: commands.Context, member: discord.Member, amount: int):
        """
        Menambah (atau mengurangi kalau negatif) Bytes seorang player.
        Pemakaian: !addbytes @user 500   atau   !addbytes @user -200
        """
        database.add_bytes(member.id, amount)
        new_total = database.get_player(member.id)["bytes"]

        verb = "ditambahkan ke" if amount >= 0 else "dikurangi dari"
        embed = discord.Embed(
            title="💰 Bytes Diubah (Admin Override)",
            description=f"`{amount:+,}` Bytes {verb} akun {member.mention}.",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Total Bytes Sekarang", value=f"`{new_total:,}`")
        await ctx.send(embed=embed)

    @commands.command(name="setbytes")
    @commands.is_owner()
    async def setbytes(self, ctx: commands.Context, member: discord.Member, amount: int):
        """
        Mengatur Bytes seorang player LANGSUNG ke angka tertentu.
        Pemakaian: !setbytes @user 10000
        """
        database.set_bytes(member.id, amount)
        embed = discord.Embed(
            title="💰 Bytes Di-set (Admin Override)",
            description=f"Bytes {member.mention} sekarang di-set ke `{max(0, amount):,}`.",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    # =====================================================
    # XP & LEVEL OVERRIDE
    # =====================================================

    @commands.command(name="addxp", aliases=["givexp"])
    @commands.is_owner()
    async def addxp(self, ctx: commands.Context, member: discord.Member, amount: int):
        """
        Menambah XP seorang player (otomatis memproses level up kalau cukup).
        Pemakaian: !addxp @user 1000
        """
        result = database.add_xp(member.id, amount)

        embed = discord.Embed(
            title="⚡ XP Ditambahkan (Admin Override)",
            description=f"`+{amount:,}` XP diberikan ke {member.mention}.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level Sekarang", value=f"`{result['new_level']}`", inline=True)
        embed.add_field(name="XP Sekarang", value=f"`{result['current_xp']}`", inline=True)
        if result["leveled_up"]:
            embed.add_field(
                name="🎉 Level Up!",
                value=f"Level {result['old_level']} ➡️ {result['new_level']}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="setlevel")
    @commands.is_owner()
    async def setlevel(self, ctx: commands.Context, member: discord.Member, level: int):
        """
        Mengatur Level seorang player LANGSUNG (XP direset ke 0).
        Pemakaian: !setlevel @user 50
        """
        if level < 1:
            await ctx.send("❌ Level minimal adalah 1.")
            return

        database.set_level(member.id, level, xp=0)
        embed = discord.Embed(
            title="📈 Level Di-set (Admin Override)",
            description=f"Level {member.mention} sekarang di-set ke `{level}` (XP direset ke 0).",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    # =====================================================
    # HEAT OVERRIDE
    # =====================================================

    @commands.command(name="setheat")
    @commands.is_owner()
    async def setheat(self, ctx: commands.Context, member: discord.Member, value: int):
        """
        Mengatur Heat seorang player LANGSUNG ke nilai tertentu (0-100),
        TANPA memicu logic arrested/jail. Untuk override murni.
        Pemakaian: !setheat @user 65
        """
        database.set_heat(member.id, value)
        new_heat = database.get_player(member.id)["heat"]

        embed = discord.Embed(
            title="🔥 Heat Di-set (Admin Override)",
            description=f"Heat {member.mention} sekarang di-set ke `{new_heat}/100`.",
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Catatan: ini TIDAK memicu status jail walau nilainya 100.")
        await ctx.send(embed=embed)

    # =====================================================
    # RIG OVERRIDE
    # =====================================================

    @commands.command(name="setrig")
    @commands.is_owner()
    async def setrig(self, ctx: commands.Context, member: discord.Member, tier: int):
        """
        Mengatur rig_level seorang player LANGSUNG (0 = belum punya hardware).
        Pemakaian: !setrig @user 3
        """
        max_tier = len(config.RIG_TIERS)
        if tier < 0 or tier > max_tier:
            await ctx.send(f"❌ Tier harus antara 0 (tidak punya rig) sampai {max_tier}.")
            return

        database.set_rig_level(member.id, tier)
        rig_name = "Tidak ada" if tier == 0 else config.RIG_TIERS[tier - 1]["name"]

        embed = discord.Embed(
            title="⚙️ Rig Level Di-set (Admin Override)",
            description=f"Hardware {member.mention} sekarang di-set ke Tier `{tier}` ({rig_name}).",
            color=discord.Color.dark_teal(),
        )
        await ctx.send(embed=embed)

    # =====================================================
    # RESET PLAYER
    # =====================================================

    @commands.command(name="resetplayer", aliases=["wipeplayer"])
    @commands.is_owner()
    async def resetplayer(self, ctx: commands.Context, member: discord.Member, confirm: str = None):
        """
        Menghapus SELURUH data seorang player (kembali ke kondisi baru).
        Butuh kata "confirm" secara eksplisit sebagai jaring pengaman,
        supaya tidak ada yang kehapus data secara tidak sengaja.

        Pemakaian: !resetplayer @user confirm
        """
        if confirm != "confirm":
            await ctx.send(
                f"⚠️ Ini akan MENGHAPUS SELURUH data {member.mention} (Bytes, Level, XP, Heat, Rig).\n"
                f"Kalau yakin, jalankan ulang dengan: `!resetplayer @{member.name} confirm`"
            )
            return

        database.reset_player(member.id)
        embed = discord.Embed(
            title="🗑️ Data Player Direset (Admin Override)",
            description=f"Seluruh data {member.mention} berhasil dihapus. Statusnya sekarang seperti player baru.",
            color=discord.Color.red(),
        )
        embed.set_footer(text=f"Dieksekusi oleh: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # =====================================================
    # DEBUG VIEW
    # =====================================================

    @commands.command(name="playerinfo", aliases=["rawdata", "debugplayer"])
    @commands.is_owner()
    async def playerinfo(self, ctx: commands.Context, member: discord.Member = None):
        """
        Menampilkan SEMUA raw data player langsung dari database,
        termasuk kolom yang tidak ditampilkan di !profile biasa
        (seperti jail_until dalam format timestamp mentah).
        Pemakaian: !playerinfo [@user]
        """
        target = member or ctx.author
        player = database.get_player(target.id)
        jail_status = database.is_jailed(target.id)

        embed = discord.Embed(
            title=f"🔍 Raw Data: {target.display_name}",
            color=discord.Color.dark_grey(),
        )
        embed.add_field(name="user_id", value=f"`{player['user_id']}`", inline=False)
        embed.add_field(name="bytes", value=f"`{player['bytes']}`", inline=True)
        embed.add_field(name="level", value=f"`{player['level']}`", inline=True)
        embed.add_field(name="xp", value=f"`{player['xp']}`", inline=True)
        embed.add_field(name="heat", value=f"`{player['heat']}`", inline=True)
        embed.add_field(name="rig_level", value=f"`{player['rig_level']}`", inline=True)
        embed.add_field(name="jail_until (raw)", value=f"`{player['jail_until']}`", inline=True)

        if jail_status["jailed"]:
            embed.add_field(
                name="Status Jail",
                value=f"🔒 Jailed, sisa `{jail_status['seconds_remaining']}` detik",
                inline=False,
            )
        else:
            embed.add_field(name="Status Jail", value="🟢 Tidak jailed", inline=False)

        embed.add_field(
            name="Unix time sekarang (referensi)",
            value=f"`{int(time.time())}`",
            inline=False,
        )
        await ctx.send(embed=embed)

    # =====================================================
    # ECONOMY STATS
    # =====================================================

    @commands.command(name="dbstats", aliases=["econstats"])
    @commands.is_owner()
    async def dbstats(self, ctx: commands.Context):
        """
        Menampilkan ringkasan statistik ekonomi seluruh server:
        total player, total Bytes beredar, rata-rata level & Bytes.
        Berguna untuk memantau kesehatan balancing game.
        Pemakaian: !dbstats
        """
        stats = database.get_economy_stats()

        embed = discord.Embed(
            title="📊 Statistik Ekonomi Server",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Total Player Terdaftar", value=f"`{stats['total_players']}`", inline=True)
        embed.add_field(name="Total Bytes Beredar", value=f"`{stats['total_bytes']:,}`", inline=True)
        embed.add_field(name="Rata-rata Level", value=f"`{stats['avg_level']}`", inline=True)
        embed.add_field(name="Rata-rata Bytes/Player", value=f"`{stats['avg_bytes']:,}`", inline=True)
        await ctx.send(embed=embed)

    # =====================================================
    # HOT RELOAD (dev convenience)
    # =====================================================

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, cog_name: str):
        """
        Reload satu cog tanpa perlu restart seluruh bot. Sangat berguna
        saat development: edit file cog, simpan, lalu !reload namanya
        di Discord, tanpa perlu Ctrl+C dan python main.py lagi.

        Pemakaian: !reload hack   (otomatis jadi cogs.hack)
        """
        extension = f"cogs.{cog_name}"
        try:
            await self.bot.reload_extension(extension)
            await ctx.send(f"🔄 Berhasil reload `{extension}`.")
        except commands.ExtensionNotLoaded:
            await ctx.send(f"❌ `{extension}` belum pernah di-load. Cek nama cog-nya.")
        except Exception as e:
            await ctx.send(f"❌ Gagal reload `{extension}`:\n```{e}```")

    # =====================================================
    # ERROR HANDLER BERSAMA
    # =====================================================

    def _get_example(self, command_name: str) -> str:
        """
        Ambil contoh pemakaian command dari dictionary COMMAND_EXAMPLES.
        Kalau command-nya tidak terdaftar di situ (misal lupa ditambahkan
        saat bikin command baru), fallback ke format generik daripada error.
        """
        return self.COMMAND_EXAMPLES.get(command_name, f"!{command_name} <argumen>")

    async def cog_command_error(self, ctx: commands.Context, error):
        """
        Menangani error untuk SEMUA command di cog ini sekaligus,
        supaya tidak perlu menulis handler error terpisah di tiap command.
        Setiap pesan error argumen kurang/salah otomatis menyertakan
        CONTOH pemakaian yang benar, supaya langsung jelas tanpa perlu
        buka dokumentasi terpisah.
        """
        example = self._get_example(ctx.command.name)

        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Command ini cuma bisa dipakai oleh Owner bot.")

        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(
                f"❌ Member tidak ditemukan. Pastikan mention/nama user-nya benar.\n"
                f"**Contoh:** `{example}`"
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Argumen kurang lengkap (kurang: `{error.param.name}`).\n"
                f"**Contoh:** `{example}`"
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ Salah satu argumen formatnya salah (misal: mention user atau angka tidak valid).\n"
                f"**Contoh:** `{example}`"
            )

        else:
            raise error


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog admin."""
    await bot.add_cog(AdminCog(bot))