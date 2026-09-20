"""
CyberHeist Bot - Shop Cog
=========================
Cog ini menangani pembelian hardware/rig via command !shop dan !buy.
"""

import discord
from discord.ext import commands

import database
import config


class ShopCog(commands.Cog):
    """Kumpulan command untuk toko hardware siber."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop", aliases=["blackmarket", "store"])
    async def shop(self, ctx: commands.Context):
        """Menampilkan daftar hardware rig yang bisa dibeli."""
        user_id = ctx.author.id
        player = database.get_player(user_id)
        user_bytes = player["bytes"]

        embed = discord.Embed(
            title="🛒 Black Market Hardware Shop",
            description=(
                f"Gunakan Bytes hasil hacking-mu untuk upgrade rig dan automatisasi penambangan!\n\n"
                f"💰 **Saldo Bytes Kamu:** `{user_bytes:,} Bytes`"
            ),
            color=discord.Color.dark_gold()
        )

        # Ambil data langsung dari config.RIG_TIERS (single source of truth)
        for rig in config.RIG_TIERS:
            tier = rig["tier"]
            name = rig["name"]
            price = rig["price"]
            income = rig["income_per_tick"]

            embed.add_field(
                name=f"Tier {tier}: {name} (Ketik `!buy {tier}`)",
                value=f"Harga: `{price:,} Bytes`\nIdle Income: `+{income} Bytes/klaim`",
                inline=False
            )

        embed.set_footer(text="Tips: Hardware tingkat tinggi memberikan passive income lebih besar.")
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, tier: int = None):
        """Membeli hardware rig berdasarkan nomor tier."""
        if tier is None:
            tier_list = ", ".join([str(rig["tier"]) for rig in config.RIG_TIERS])
            await ctx.send(f"❌ Masukkan nomor tier yang ingin dibeli, contoh: `!buy 1`.\nTier tersedia: {tier_list}")
            return

        # Cari tier di config.RIG_TIERS (single source of truth)
        selected_rig = None
        for rig in config.RIG_TIERS:
            if rig["tier"] == tier:
                selected_rig = rig
                break

        if selected_rig is None:
            tier_list = ", ".join([str(rig["tier"]) for rig in config.RIG_TIERS])
            await ctx.send(f"❌ Tier hardware tidak valid! Tier tersedia: {tier_list}")
            return

        user_id = ctx.author.id
        player = database.get_player(user_id)

        if player["rig_level"] >= tier:
            current_rig_name = config.RIG_TIERS[player["rig_level"] - 1]["name"]
            await ctx.send(
                f"❌ Kamu sudah memiliki **{current_rig_name}** (Tier {player['rig_level']})!\n"
                f"Kamu tidak bisa membeli hardware tier yang sama atau lebih rendah."
            )
            return

        if player["bytes"] < selected_rig["price"]:
            await ctx.send(
                f"❌ Bytes kamu tidak cukup untuk membeli **{selected_rig['name']}** (Tier {tier})!\n"
                f"Butuh **{selected_rig['price']:,} Bytes**, saldo kamu saat ini: `{player['bytes']:,} Bytes`."
            )
            return

        database.add_bytes(user_id, -selected_rig["price"])
        database.set_rig_level(user_id, tier)

        await ctx.send(
            f"✅ Berhasil membeli **{selected_rig['name']}** seharga **{selected_rig['price']:,} Bytes**! "
            f"Sistem penambangan siber ditingkatkan (Sekarang Tier {tier})."
        )


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog shop."""
    await bot.add_cog(ShopCog(bot))