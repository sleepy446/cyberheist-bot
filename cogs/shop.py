"""
CyberHeist Bot - Shop & Rig Cog
=================================
Cog ini menangani sistem ekonomi lanjutan: melihat daftar hardware
di toko (!shop) dan membeli upgrade rig (!rig) untuk passive income.
"""

import discord
from discord.ext import commands

import database
import config


class ShopCog(commands.Cog):
    """Kumpulan command untuk belanja hardware dan upgrade rig."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop", aliases=["rigs", "store"])
    async def shop(self, ctx: commands.Context):
        """
        Menampilkan daftar hardware/rig yang tersedia untuk dibeli.
        Pemakaian di Discord: !shop
        """
        embed = discord.Embed(
            title="🛒 Black Market Hardware Shop",
            description="Gunakan Bytes hasil hacking-mu untuk upgrade rig dan otomatisasi penambangan!",
            color=discord.Color.blue()
        )

        for item in config.RIG_TIERS:
            tier = item["tier"]
            name = item["name"]
            price = item["price"]
            income = item["income_per_tick"]

            embed.add_field(
                name=f"Tier {tier}: {name}",
                value=f"💰 Harga: **{price:,} Bytes**\n⚙️ Idle Income: **+{income} Bytes/klaim**\n💡 Ketik `!buy {tier}` untuk membeli.",
                inline=False
            )

        embed.set_footer(text="Tips: Hardware tingkat tinggi memberikan passive income lebih besar.")
        await ctx.send(embed=embed)

    @commands.command(name="buy", aliases=["upgrade"])
    async def buy(self, ctx: commands.Context, tier: int = None):
        """
        Membeli atau mengupgrade rig ke tier tertentu.
        Pemakaian di Discord: !buy <tier_number> (Contoh: !buy 1)
        """
        if tier is None:
            await ctx.send("⚠️ Masukkan nomor tier rig yang ingin dibeli! Contoh: `!buy 1`. Ketik `!shop` untuk melihat daftar.")
            return

        # Validasi apakah tier yang diminta ada di config.py
        target_tier = None
        for item in config.RIG_TIERS:
            if item["tier"] == tier:
                target_tier = item
                break

        if target_tier is None:
            await ctx.send(f"❌ Tier hardware `{tier}` tidak ditemukan di Black Market!")
            return

        user_id = ctx.author.id
        player = database.get_player(user_id)
        current_rig_level = player["rig_level"]

        # Validasi urutan upgrade (harus berurutan atau tidak boleh downgrade)
        if tier <= current_rig_level:
            if tier == current_rig_level:
                await ctx.send(f"⚠️ Kamu sudah memiliki **{target_tier['name']}**!")
            else:
                await ctx.send("⚠️ Kamu tidak bisa membeli hardware yang tier-nya di bawah rig kamu saat ini!")
            return

        if tier != current_rig_level + 1:
            await ctx.send(f"⚠️ Kamu harus upgrade secara berurutan! Rig kamu saat ini ada di Tier {current_rig_level}, jadi kamu harus membeli Tier {current_rig_level + 1} terlebih dahulu.")
            return

        # Cek apakah Bytes player cukup
        cost = target_tier["price"]
        if player["bytes"] < cost:
            shortage = cost - player["bytes"]
            await ctx.send(f"❌ Bytes tidak cukup! Kamu butuh **{cost:,} Bytes** (Kurang `{shortage:,} Bytes`). Terus `!hack` dulu!")
            return

        # Proses Transaksi: Kurangi Bytes, update rig_level
        database.add_bytes(user_id, -cost)
        database.set_rig_level(user_id, tier)

        embed = discord.Embed(
            title="🎉 Pembelian Berhasil!",
            description=f"Selamat, {ctx.author.mention}! Kamu berhasil mengupgrade rig-mu ke **Tier {tier}: {target_tier['name']}**!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💸 Biaya", value=f"-{cost:,} Bytes", inline=True)
        embed.add_field(name="⚙️ Passive Income Baru", value=f"+{target_tier['income_per_tick']} Bytes/klaim", inline=True)
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog shop."""
    await bot.add_cog(ShopCog(bot))