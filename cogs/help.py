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

    @commands.command(name="help")
    async def help_player(self, ctx: commands.Context):
        """Menampilkan daftar command untuk player."""
        embed = discord.Embed(
            title="CyberHeist - Player Command List",
            description="Daftar command yang tersedia untuk player:",
            color=discord.Color.green()
        )
        
        # Filtering commands based on whether they are for player
        # Simple filter: skip admin commands
        for cmd in self.bot.commands:
            if cmd.name in ["ping", "help", "ahelp"]:
                continue
            
            # This is a heuristic, in a real bot, we might use categories
            # For now, let's assume all commands NOT in admin.py are player commands
            # Or check if they have is_owner check
            is_admin = False
            for check in cmd.checks:
                if check.__qualname__ == "is_owner.<locals>.predicate":
                    is_admin = True
                    break
            
            if not is_admin:
                embed.add_field(name=f"!{cmd.name}", value=cmd.help or "Tidak ada deskripsi.", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="ahelp")
    @commands.is_owner()
    async def help_admin(self, ctx: commands.Context):
        """Menampilkan daftar command untuk admin."""
        embed = discord.Embed(
            title="CyberHeist - Admin Command List",
            description="Daftar command khusus Admin/Owner:",
            color=discord.Color.red()
        )
        
        for cmd in self.bot.commands:
            # Check if command has is_owner check
            is_admin = False
            for check in cmd.checks:
                if check.__qualname__ == "is_owner.<locals>.predicate":
                    is_admin = True
                    break
            
            if is_admin:
                embed.add_field(name=f"!{cmd.name}", value=cmd.help or "Tidak ada deskripsi.", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
