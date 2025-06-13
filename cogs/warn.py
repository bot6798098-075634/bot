import discord
from discord import app_commands
from discord.ext import commands
import json
import os

WARNINGS_FILE = "warnings.json"

def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_warnings(warnings_data):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(warnings_data, f, indent=4)

class WarnCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = load_warnings()

    @app_commands.command(name="warn", description="Warn a user for a specific reason.")
    async def warn_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        user_id = str(user.id)

        if user_id not in self.warnings:
            self.warnings[user_id] = []

        self.warnings[user_id].append(reason)
        save_warnings(self.warnings)

        embed = discord.Embed(
            title="User Warned",
            description=f"{user.mention} has been warned for:\n`{reason}`",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Warned by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(WarnCog(bot))
