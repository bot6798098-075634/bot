import discord
from discord import app_commands
from discord.ext import commands

class UptimeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="up_time", description="Show how long the bot has been running.")
    async def uptime_slash(self, interaction: discord.Interaction):
        now = discord.utils.utcnow()
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
            title="🕒 Bot Uptime",
            description=f"The bot has been online for:\n**{uptime_str}**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Thanks for keeping me running!")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UptimeCog(bot))
