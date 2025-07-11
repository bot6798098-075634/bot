import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone

class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot's latency and uptime")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)  # in ms
        now = datetime.now(timezone.utc)
        uptime_duration = now - self.bot.start_time
        uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))
        
        embed = discord.Embed(
            title=f"{logo_emoji} SWAT Roleplay Community",
            description=(
                "Information about the bot status\n"
                f"> {pong_emoji} Latency: `{latency} ms`\n"
                f"> {time_emoji} Uptime: `{uptime_str}`\n"
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            ),
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="SWAT Roleplay Community")
        await interaction.response.send_message(embed=embed)

    async def cog_load(self):
        self.bot.tree.add_command(self.ping_slash)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
