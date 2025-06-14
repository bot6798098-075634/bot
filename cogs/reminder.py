import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remindme", description="Set a reminder")
    async def remindme_slash(self, interaction: discord.Interaction, time: int, reminder: str):
        await interaction.response.send_message(f"⏰ Reminder set for {time} seconds: {reminder}", ephemeral=True)

        await asyncio.sleep(time)

        await interaction.channel.send(f"🔔 Reminder for {interaction.user.mention}: {reminder}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Reminder(bot))
