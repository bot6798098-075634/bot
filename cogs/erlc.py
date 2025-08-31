# cogs/erlc_group.py
import discord
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1343179590247645205  # replace with your server ID

class ERLCGroup(commands.Cog):
    """Base ERLC command group."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.erlc = app_commands.Group(name="erlc", description="ER:LC commands")

    @commands.Cog.listener()
    async def on_ready(self):
        guild = discord.Object(id=GUILD_ID)
        self.bot.tree.add_command(self.erlc, guild=guild)
        await self.bot.tree.sync(guild=guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(ERLCGroup(bot))
