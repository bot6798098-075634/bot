import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

class Uptime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="uptime", description="Show how long the bot has been running.")
    async def uptime_slash(self, interaction: discord.Interaction):
        now = datetime.now(timezone.utc)
        uptime_seconds = int((now - self.bot.start_time).total_seconds())

        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        def format_time(unit, label):
            return f"{unit} {label}{'s' if unit != 1 else ''}"

        uptime_parts = [
            format_time(days, "day"),
            format_time(hours, "hour"),
            format_time(minutes, "minute"),
            format_time(seconds, "second")
        ]

        uptime_str = ", ".join(part for part in uptime_parts if not part.startswith("0"))

        embed = discord.Embed(
            title=f"{time_emoji} Bot Uptime",
            description=f"The bot has been online for:\n**{uptime_str}**",
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")

        await interaction.response.send_message(embed=embed)

    async def cog_load(self):
        self.bot.tree.add_command(self.uptime_slash)

async def setup(bot: commands.Bot):
    await bot.add_cog(Uptime(bot))
