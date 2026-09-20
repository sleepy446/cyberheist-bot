"""
CyberHeist Bot - Help Cog
=========================
Cog ini menangani command !help untuk player dan !ahelp untuk Admin/Owner.
"""

import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_admin_command(self, cmd: commands.Command) -> bool:
        """
        Mengecek apakah command adalah admin command dengan cara lebih robust.
        Cek: (1) command ada di AdminCog, atau (2) punya @commands.is_owner() decorator
        """
        # Cek 1: Apakah command ini ada di cog bernama "AdminCog"?
        if cmd.cog and cmd.cog.__class__.__name__ == "AdminCog":
            return True

        # Cek 2: Apakah command punya is_owner check?
        for check in cmd.checks:
            check_name = getattr(check, "__qualname__", "")
            if "is_owner" in check_name:
                return True

        return False

    @commands.command(name="help")
    async def help_player(self, ctx: commands.Context):
        """Menampilkan daftar command untuk player."""
        embed = discord.Embed(
            title="🕵️ CyberHeist - Player Commands",
            description="Daftar command yang tersedia untuk player:",
            color=discord.Color.green()
        )

        player_commands = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            # Skip utility commands dan admin commands
            if cmd.name in ["ping", "help", "ahelp"]:
                continue

            if not self._is_admin_command(cmd):
                # Ambil aliases jika ada
                aliases = f" (alias: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                description = cmd.help or "Tidak ada deskripsi."
                player_commands.append(f"**!{cmd.name}**{aliases}\n└─ {description}")

        if player_commands:
            embed.description += "\n\n" + "\n\n".join(player_commands)
        else:
            embed.description += "\n\nTidak ada command player yang tersedia."

        embed.set_footer(text="Gunakan !help untuk melihat list ini kapan saja.")
        await ctx.send(embed=embed)

    @commands.command(name="ahelp")
    @commands.is_owner()
    async def help_admin(self, ctx: commands.Context):
        """Menampilkan daftar command untuk admin."""
        embed = discord.Embed(
            title="🔧 CyberHeist - Admin Commands",
            description="Daftar command khusus Admin/Owner:",
            color=discord.Color.red()
        )

        admin_commands = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            if self._is_admin_command(cmd):
                aliases = f" (alias: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                description = cmd.help or "Tidak ada deskripsi."
                admin_commands.append(f"**!{cmd.name}**{aliases}\n└─ {description}")

        if admin_commands:
            embed.description += "\n\n" + "\n\n".join(admin_commands)
        else:
            embed.description += "\n\nTidak ada admin command yang tersedia."

        embed.set_footer(text="Command ini hanya bisa digunakan oleh Owner bot.")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
