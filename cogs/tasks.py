"""
CyberHeist Bot - Background Tasks Cog
=====================================
Menangani task periodik seperti passive heat decay.
"""

from discord.ext import tasks, commands
import database
import config

class PassiveTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.passive_heat_decay.start()

    def cog_unload(self):
        self.passive_heat_decay.cancel()

    @tasks.loop(minutes=1)
    async def passive_heat_decay(self):
        """
        Mengurangi heat player secara perlahan (passive decay)
        agar player tidak terjebak di posisi kritis.
        Target: ~30-40 poin dalam 8 menit -> ~5 poin/menit.
        """
        players = database.get_players_with_heat()
        for player in players:
            # Mengurangi 5 poin setiap menit. add_heat otomatis melakukan clamp [0, 100]
            database.add_heat(player["user_id"], -5)

    @passive_heat_decay.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(PassiveTaskCog(bot))
