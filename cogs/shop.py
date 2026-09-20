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
            # PERBAIKAN BUG: discord.Color.dark_embed() TIDAK ADA di discord.py,
            # ini bikin !shop crash (AttributeError) tiap kali dipanggil.
            # Diganti ke discord.Color.dark_gold() yang valid & masih cocok tema black market.
            color=discord.Color.dark_gold()
        )

        embed.add_field(
            name="Tier 1: Botnet Kecil (Ketik `!buy 1`)",
            value="Harga: `500 Bytes`\nIdle Income: `+5 Bytes/klaim`",
            inline=False
        )
        embed.add_field(
            name="Tier 2: GPU Rig (Ketik `!buy 2`)",
            value="Harga: `2,500 Bytes`\nIdle Income: `+30 Bytes/klaim`",
            inline=False
        )
        embed.add_field(
            name="Tier 3: Server Rack (Ketik `!buy 3`)",
            value="Harga: `10,000 Bytes`\nIdle Income: `+150 Bytes/klaim`",
            inline=False
        )

        embed.set_footer(text="Tips: Hardware tingkat tinggi memberikan passive income lebih besar.")
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, tier: int = None):
        """Membeli hardware rig berdasarkan nomor tier (1, 2, atau 3)."""
        if tier is None:
            await ctx.send("❌ Masukkan nomor tier yang ingin dibeli, contoh: `!buy 1`, `!buy 2`, atau `!buy 3`.")
            return

        items = {
            1: {"name": "Botnet Kecil (Tier 1)", "price": 500},
            2: {"name": "GPU Rig (Tier 2)", "price": 2500},
            3: {"name": "Server Rack (Tier 3)", "price": 10000}
        }

        if tier not in items:
            await ctx.send("❌ Tier hardware tidak valid! Pilih tier 1, 2, atau 3.")
            return

        selected_item = items[tier]
        user_id = ctx.author.id
        player = database.get_player(user_id)

        if player["rig_level"] >= tier:
            await ctx.send(
                f"❌ Kamu sudah memiliki **{config.RIG_TIERS[player['rig_level'] - 1]['name']}** (Tier {player['rig_level']})!\n"
                f"Kamu tidak bisa membeli hardware tier yang sama atau lebih rendah."
            )
            return

        if player["bytes"] < selected_item["price"]:
            await ctx.send(
                f"❌ Bytes kamu tidak cukup untuk membeli **{selected_item['name']}**!\n"
                f"Butuh **{selected_item['price']:,} Bytes**, saldo kamu saat ini: `{player['bytes']:,} Bytes`."
            )
            return

        database.add_bytes(user_id, -selected_item["price"])
        database.set_rig_level(user_id, tier)

        await ctx.send(
            f"✅ Berhasil membeli **{selected_item['name']}** seharga **{selected_item['price']:,} Bytes**! "
            f"Sistem penambangan siber ditingkatkan (Sekarang Tier {tier})."
        )


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog shop."""
    await bot.add_cog(ShopCog(bot))