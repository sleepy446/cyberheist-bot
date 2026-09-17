"""
CyberHeist Bot - Hack Cog (Grinding Core)
=========================================
Cog ini menangani mekanika inti permainan: grinding manual via !hack.
Mengatur perolehan Bytes, XP, kenaikan Level, dan akumulasi Heat (risiko).
"""

import random
import discord
from discord.ext import commands

import database
import config


class HackCog(commands.Cog):
    """Kumpulan command untuk aksi peretasan/grinding."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hack")
    @commands.cooldown(1, 4, commands.BucketType.user)  # Cooldown 4 detik biar gak spam macro
    async def hack(self, ctx: commands.Context):
        """
        Command utama grinding: meretas target kecil untuk dapet Bytes & XP,
        tapi menaikkan Heat (tingkat buronan).
        Pemakaian di Discord: !hack
        """
        user_id = ctx.author.id

        # Pastikan player terdaftar di database
        player = database.get_player(user_id)

        # Cek dulu apakah heat saat ini sudah di ambang batas maksimal (100)
        # Jika player nekat hack saat heat sudah 100, langsung digerebek tanpa dapet hasil!
        if player["heat"] >= config.HEAT_MAX:
            heat_result = database.add_heat(user_id, 0) # Trigger reset & denda dari database
            
            jail_embed = discord.Embed(
                title="🚨 CEROBOH! SERVER TERLACAK & DIGEREBEK!",
                description=f"Sial, {ctx.author.mention}! Heat kamu sudah mentok di **100/100** tapi kamu masih nekat nge-hack. Tim Cyber Crime langsung mendobrak pintu rumahmu!",
                color=discord.Color.red()
            )
            jail_embed.add_field(name="💸 Denda Penyitaan", value=f"-{heat_result['fine']:,} Bytes disita oleh pihak berwenang.", inline=False)
            jail_embed.add_field(name="🛡️ Status Karantina", value="Aksi gagal total! Hardware disita sementara dan Heat di-reset ke `0/100`.", inline=False)
            jail_embed.set_footer(text="Gunakan !clean secara berkala sebelum heat penuh!")
            await ctx.send(embed=jail_embed)
            return

        # 1. Hitung perolehan Bytes dan XP secara acak jika aman
        earned_bytes = random.randint(20, 60)
        earned_xp = random.randint(15, 35)

        # 2. Masukkan ke database
        database.add_bytes(user_id, earned_bytes)
        xp_result = database.add_xp(user_id, earned_xp)
        
        # 3. Tambah Heat
        heat_result = database.add_heat(user_id, config.HEAT_GAIN_PER_HACK)
        new_heat = heat_result["heat"]

        # 4. Buat narasi acak target hack
        targets = [
            "Wi-Fi Cafe Samping Gang",
            "Sistem Parkir Otomatis Minimarket",
            "Database Lokal RT/RW",
            "ATM Rusak di Ujung Jalan",
            "Server Gudang Toko Online"
        ]
        target_name = random.choice(targets)

        # 5. Susun Embed Respon Utama
        embed = discord.Embed(
            title="💻 Infiltrasi Berhasil!",
            description=f"Berhasil meretas **{target_name}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Bytes Didapat", value=f"+{earned_bytes:,} Bytes", inline=True)
        embed.add_field(name="⚡ XP Didapat", value=f"+{earned_xp} XP", inline=True)
        
        # Indikator Heat dengan peringatan jika mendekati zona merah
        heat_warning = ""
        if new_heat >= config.HEAT_DANGER_THRESHOLD:
            heat_warning = "\n⚠️ **PERINGATAN: Heat tinggi! Segera jalankan `!clean`!**"
        
        embed.add_field(name="🔥 Heat Level", value=f"{new_heat}/100{heat_warning}", inline=False)
        embed.set_footer(text=f"Hacker: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

        # 6. Jika penambahan heat dari hack ini membuatnya pas menyentuh/lewat 100
        if heat_result["arrested"]:
            jail_embed = discord.Embed(
                title="🚨 SERVER TERLACAK - ANDA DIGEREBEK!",
                description=f"Sial, {ctx.author.mention}! Heat kamu mencapai **100/100**. Tim Cyber Crime berhasil melacak lokasimu!",
                color=discord.Color.red()
            )
            jail_embed.add_field(name="💸 Denda Penyitaan", value=f"-{heat_result['fine']:,} Bytes disita oleh pihak berwenang.", inline=False)
            jail_embed.add_field(name="🛡️ Status Karantina", value="Hardware diputus sementara. Heat di-reset ke `0/100`.", inline=False)
            jail_embed.set_footer(text="Hati-hati ke depannya. Jangan lupa !clean sebelum heat mentok!")
            await ctx.send(embed=jail_embed)

        # 7. Jika player naik level, kirim pesan tambahan
        if xp_result["leveled_up"]:
            level_embed = discord.Embed(
                title="🎉 LEVEL UP!",
                description=f"Hebat, {ctx.author.mention}! Kamu naik dari Level **{xp_result['old_level']}** ➡️ **{xp_result['new_level']}**!",
                color=discord.Color.gold()
            )
            await ctx.send(embed=level_embed)

    @hack.error
    async def hack_error(self, ctx: commands.Context, error):
        """Menangani error cooldown command !hack."""
        if isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after, 1)
            await ctx.send(f"⏳ Sistem pendinginan perangkat... Tunggu **{remaining} detik** lagi sebelum nge-hack ulang.", delete_after=5)
        else:
            raise error


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog hack."""
    await bot.add_cog(HackCog(bot))