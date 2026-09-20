"""
CyberHeist Bot - Profile Cog
==============================
Cog ini menangani command yang berkaitan dengan menampilkan status
player: !profile, !stats (alias), dan !leaderboard.
"""

import discord
from discord.ext import commands

import database
import config


def make_progress_bar(current: int, max_val: int, length: int = 10, fill_char: str = "█", empty_char: str = "░") -> str:
    """Membuat visual progress bar sederhana untuk Discord Embed."""
    if max_val <= 0:
        return empty_char * length
    percent = current / max_val
    filled = round(percent * length)
    filled = max(0, min(length, filled))
    return (fill_char * filled) + (empty_char * (length - filled))


class ProfileCog(commands.Cog):
    """Kumpulan command untuk menampilkan status/profil player."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["stats"])
    async def profile(self, ctx: commands.Context):
        """
        Menampilkan status player: Level, Bytes, XP, Heat, Rig, dan
        status Jail (kalau sedang dalam masa karantina setelah arrested).
        Pemakaian di Discord: !profile atau !stats
        """
        player = database.get_player(ctx.author.id)

        xp_needed = config.xp_required_for_level(player["level"])
        xp_percent = round((player["xp"] / xp_needed) * 100) if xp_needed > 0 else 0
        xp_bar = make_progress_bar(player["xp"], xp_needed, length=10)

        heat = player["heat"]
        if heat >= config.HEAT_DANGER_THRESHOLD:
            heat_status = "🔴 BAHAYA - Segera !clean!"
        elif heat >= config.HEAT_DANGER_THRESHOLD // 2:
            heat_status = "🟡 Waspada"
        else:
            heat_status = "🟢 Aman"

        heat_bar = make_progress_bar(heat, config.HEAT_MAX, length=10)

        if player["rig_level"] == 0:
            rig_name = "Belum ada hardware"
        else:
            rig_name = config.RIG_TIERS[player["rig_level"] - 1]["name"]

        jail_status = database.is_jailed(ctx.author.id)

        embed = discord.Embed(
            title=f"🕵️ Profil Hacker: {ctx.author.display_name}",
            color=discord.Color.dark_purple(),
        )
        embed.add_field(name="Level", value=f"`{player['level']}`", inline=True)
        embed.add_field(name="Bytes", value=f"`{player['bytes']:,}`", inline=True)
        embed.add_field(name="Hardware", value=f"`{rig_name}`", inline=True)

        embed.add_field(
            name="XP Progress",
            value=f"`{xp_bar}` `{player['xp']} / {xp_needed}` ({xp_percent}%)",
            inline=False
        )
        embed.add_field(
            name="Heat Level",
            value=f"`{heat_bar}` `{heat}/100` — {heat_status}",
            inline=False
        )

        if jail_status["jailed"]:
            remaining = jail_status["seconds_remaining"]
            minutes, seconds = divmod(remaining, 60)
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

            embed.add_field(
                name="🔒 Status Karantina",
                value=(
                    f"**DALAM PENGAWASAN** - tidak bisa `!hack`\n"
                    f"Sisa waktu: **{time_str}**"
                ),
                inline=False,
            )
            embed.color = discord.Color.red()

        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx: commands.Context):
        """
        Menampilkan peringkat hacker terkaya (global - karena data
        player bersifat satu wallet untuk semua server Discord).
        Pemakaian: !leaderboard
        """
        leaderboard_data = database.get_leaderboard(limit=10)

        if not leaderboard_data:
            await ctx.send("📭 Belum ada data hacker di database.")
            return

        embed = discord.Embed(
            title="🏆 Papan Peringkat Hacker (Top 10)",
            description="Daftar hacker paling makmur.",
            color=discord.Color.gold()
        )

        leaderboard_list = []
        for index, row in enumerate(leaderboard_data, 1):
            user_id = row["user_id"]
            try:
                member = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                name = member.display_name
            except Exception:
                name = f"Hacker Tersembunyi #{user_id}"

            medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"`#{index}`"
            leaderboard_list.append(f"{medal} **{name}** — Level `{row['level']}` | `{row['bytes']:,}` Bytes")

        embed.description = "\n".join(leaderboard_list)
        embed.set_footer(text="Kejar peringkat teratas dengan rajin !hack dan !net!")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Fungsi wajib yang dipanggil discord.py saat cog ini di-load."""
    await bot.add_cog(ProfileCog(bot))