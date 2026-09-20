"""
CyberHeist Bot - Daily Reward Cog
===================================
Cog ini menangani sistem Daily Reward dengan streak mechanism.
Reset harian berbasis UTC (00:00 UTC).
"""

import random
import discord
from discord import app_commands
from discord.ext import commands

import database
import config


class DailyCog(commands.Cog):
    """Kumpulan command untuk daily reward system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Klaim hadiah harian, streak bonus, dan mystery drop (reset 00:00 UTC)")
    @app_commands.checks.cooldown(1, config.DAILY_COOLDOWN_SECONDS, key=lambda i: i.user.id)
    async def daily(self, interaction: discord.Interaction):
        """
        Klaim reward harian dengan streak bonus dan mystery drop.
        Reset setiap hari di 00:00 UTC.
        Pemakaian di Discord: /daily
        """
        user_id = interaction.user.id
        daily_status = database.get_daily_status(user_id)

        # Jika sudah klaim hari ini, tampilkan countdown
        if not daily_status["can_claim"]:
            seconds_remaining = daily_status["seconds_until_reset"]
            hours, remainder = divmod(seconds_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours}j {minutes}m {seconds}s"

            embed = discord.Embed(
                title="⏰ Daily Reward Sudah Diklaim",
                description=f"{interaction.user.mention}, kamu sudah mengambil jatah harian hari ini!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🔥 Streak Aktif",
                value=f"**{daily_status['current_streak']} Hari**",
                inline=True
            )
            embed.add_field(
                name="⏳ Reset Dalam",
                value=f"**{time_str}**",
                inline=True
            )
            embed.set_footer(text="Kembali lagi setelah reset 00:00 UTC untuk melanjutkan streak!")
            await interaction.response.send_message(embed=embed)
            return

        # --- MULAI PROSES KLAIM ---

        # 1. Roll base bytes
        base_bytes = random.randint(
            config.DAILY_BASE_BYTES_MIN,
            config.DAILY_BASE_BYTES_MAX
        )

        # 2. Hitung streak bonus (capped)
        next_streak = daily_status["next_streak"]
        streak_bonus = min(
            config.DAILY_STREAK_BONUS_MAX,
            next_streak * config.DAILY_STREAK_BONUS_PER_DAY
        )

        # 3. Roll mystery bonus drop (weighted random)
        bonus_roll = random.randint(1, 100)

        if bonus_roll <= 40:
            # 40% - Extra Bytes
            bonus_type = "extra_bytes"
            bonus_value = random.randint(
                config.DAILY_BONUS_EXTRA_BYTES_MIN,
                config.DAILY_BONUS_EXTRA_BYTES_MAX
            )
            bonus_name = "📦 Data Leak Bounty"
            bonus_desc = f"+{bonus_value} Bytes"
            bonus_emoji = "💰"
        elif bonus_roll <= 70:
            # 30% - Bonus XP
            bonus_type = "xp"
            bonus_value = random.randint(
                config.DAILY_BONUS_XP_MIN,
                config.DAILY_BONUS_XP_MAX
            )
            bonus_name = "🧠 Zero-Day Exploit Script"
            bonus_desc = f"+{bonus_value} XP"
            bonus_emoji = "⚡"
        elif bonus_roll <= 90:
            # 20% - Heat Reduction
            bonus_type = "heat"
            bonus_value = random.randint(
                config.DAILY_BONUS_HEAT_REDUCE_MIN,
                config.DAILY_BONUS_HEAT_REDUCE_MAX
            )
            bonus_name = "🛡️ Clean VPN Proxy Tunnel"
            bonus_desc = f"-{bonus_value} Heat"
            bonus_emoji = "🔥"
        else:
            # 10% - Cipher Drop
            bonus_type = "cipher"
            bonus_value = random.randint(
                config.DAILY_BONUS_CIPHER_BYTES_MIN,
                config.DAILY_BONUS_CIPHER_BYTES_MAX
            )
            bonus_name = "🔐 Encrypted Master Key"
            bonus_desc = f"+{bonus_value} Bytes"
            bonus_emoji = "💎"

        # 4. Eksekusi claim ke database
        claim_result = database.claim_daily_reward(
            user_id=user_id,
            base_bytes=base_bytes,
            streak_bonus=streak_bonus,
            bonus_type=bonus_type,
            bonus_value=bonus_value
        )

        if not claim_result["success"]:
            # Race condition / sudah diklaim di thread lain
            await interaction.response.send_message(
                "❌ Terjadi error: Daily reward sudah diklaim!",
                ephemeral=True
            )
            return

        # 5. Buat embed response
        is_new_streak = (next_streak == 1)
        streak_status = "🆕 Streak Dimulai!" if is_new_streak else f"🔥 Streak Berlanjut: **{next_streak} Hari**"

        embed = discord.Embed(
            title="🎁 Daily Reward Diklaim!",
            description=f"Selamat {interaction.user.mention}! Kamu mendapatkan hadiah harian!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="💰 Base Reward",
            value=f"+{base_bytes:,} Bytes",
            inline=True
        )
        embed.add_field(
            name="🔥 Streak Bonus",
            value=f"+{streak_bonus:,} Bytes",
            inline=True
        )
        embed.add_field(
            name=f"{bonus_emoji} Mystery Drop",
            value=f"**{bonus_name}**\n{bonus_desc}",
            inline=False
        )
        embed.add_field(
            name="📊 Total Bytes",
            value=f"**+{claim_result['total_bytes_gain']:,} Bytes**",
            inline=True
        )
        embed.add_field(
            name="🎯 Status Streak",
            value=streak_status,
            inline=True
        )

        embed.set_footer(text="Reset harian: 00:00 UTC • Jangan lewatkan esok hari untuk lanjutkan streak!")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        # 6. Kirim notifikasi level up jika ada
        if claim_result["level_up_result"] and claim_result["level_up_result"]["leveled_up"]:
            level_result = claim_result["level_up_result"]
            level_embed = discord.Embed(
                title="🎉 LEVEL UP!",
                description=f"Bonus XP dari daily reward membuatmu naik level, {interaction.user.mention}!",
                color=discord.Color.gold()
            )
            level_embed.add_field(
                name="Level Baru",
                value=f"**{level_result['old_level']}** ➡️ **{level_result['new_level']}**",
                inline=False
            )
            await interaction.followup.send(embed=level_embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib untuk load cog daily."""
    await bot.add_cog(DailyCog(bot))
