import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot's latency")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)  # in ms
        now = datetime.now(timezone.utc)
        uptime_duration = now - self.bot.start_time
        uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

        embed = discord.Embed(
            title="SWAT Roleplay Community",
            description=(
                "Information about the bot status\n"
                f"> 🏓 Latency: `{latency} ms`\n"
                f"> ⏱️ Uptime: `{uptime_str}`"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        await interaction.response.send_message(embed=embed)

    # This is needed for slash commands to register with tree
    async def cog_load(self):
        self.bot.tree.add_command(self.ping_slash)

async def setup(bot):
    await bot.add_cog(PingCog(bot))
