"""
CyberHeist Bot - Shop Cog
=========================
Cog ini menangani pembelian hardware/rig via slash command /shop dan /buy.
"""

from typing import List
import discord
from discord import app_commands
from discord.ext import commands

import database
import config


class ShopCog(commands.Cog):
    """Kumpulan command untuk toko hardware siber."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Lihat hardware mining yang tersedia di Black Market")
    async def shop(self, interaction: discord.Interaction):
        """Menampilkan daftar hardware rig yang bisa dibeli."""
        user_id = interaction.user.id
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
                name=f"Tier {tier}: {name} (Gunakan `/buy {tier}`)",
                value=f"Harga: `{price:,} Bytes`\nIdle Income: `+{income} Bytes/klaim`",
                inline=False
            )

        embed.set_footer(text="Tips: Hardware tingkat tinggi memberikan passive income lebih besar.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Beli hardware penambangan siber berdasarkan nomor tier")
    @app_commands.describe(tier="Pilih tier hardware yang ingin dibeli")
    async def buy(self, interaction: discord.Interaction, tier: int):
        """Membeli hardware rig berdasarkan nomor tier."""
        # Cari tier di config.RIG_TIERS (single source of truth)
        selected_rig = None
        for rig in config.RIG_TIERS:
            if rig["tier"] == tier:
                selected_rig = rig
                break

        if selected_rig is None:
            tier_list = ", ".join([f"Tier {rig['tier']} ({rig['name']})" for rig in config.RIG_TIERS])
            await interaction.response.send_message(
                f"❌ Tier hardware tidak valid! Tier tersedia:\n{tier_list}",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        player = database.get_player(user_id)

        if player["rig_level"] >= tier:
            current_rig_name = config.RIG_TIERS[player["rig_level"] - 1]["name"]
            await interaction.response.send_message(
                f"❌ Kamu sudah memiliki **{current_rig_name}** (Tier {player['rig_level']})!\n"
                f"Kamu tidak bisa membeli hardware tier yang sama atau lebih rendah.",
                ephemeral=True
            )
            return

        if player["bytes"] < selected_rig["price"]:
            await interaction.response.send_message(
                f"❌ Bytes kamu tidak cukup untuk membeli **{selected_rig['name']}** (Tier {tier})!\n"
                f"Butuh **{selected_rig['price']:,} Bytes**, saldo kamu saat ini: `{player['bytes']:,} Bytes`.",
                ephemeral=True
            )
            return

        database.add_bytes(user_id, -selected_rig["price"])
        database.set_rig_level(user_id, tier)

        await interaction.response.send_message(
            f"✅ Berhasil membeli **{selected_rig['name']}** seharga **{selected_rig['price']:,} Bytes**! "
            f"Sistem penambangan siber ditingkatkan (Sekarang Tier {tier})."
        )

    @buy.autocomplete("tier")
    async def buy_tier_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
        """Memberikan autocomplete pilihan hardware tier beserta nama dan harga."""
        choices = []
        for rig in config.RIG_TIERS:
            tier_str = str(rig["tier"])
            tier_name = rig["name"]
            tier_price = f"{rig['price']:,} Bytes"
            label = f"Tier {tier_str}: {tier_name} ({tier_price})"

            # Filter berdasarkan input user jika ada
            if current.lower() in label.lower() or current in tier_str:
                choices.append(app_commands.Choice(name=label, value=rig["tier"]))

        return choices[:25]  # Discord limit maksimal 25 choices


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog shop."""
    await bot.add_cog(ShopCog(bot))
