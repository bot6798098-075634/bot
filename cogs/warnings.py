import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
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

    @app_commands.command(name="unwarn", description="Remove a specific warning from a user")
    async def unwarn_slash(self, interaction: discord.Interaction, user: discord.Member):
        user_id = str(user.id)

        if user_id in self.warnings and self.warnings[user_id]:
            options = [
                discord.SelectOption(
                    label=f"Warning {i+1}",
                    description=warn[:100] if len(warn) <= 100 else warn[:97] + "...",
                    value=str(i)
                )
                for i, warn in enumerate(self.warnings[user_id])
            ]

            select = Select(placeholder="Choose a warning to remove", options=options)

            async def select_callback(select_interaction: discord.Interaction):
                index = int(select.values[0])
                removed_warning = self.warnings[user_id].pop(index)
                save_warnings(self.warnings)

                embed = discord.Embed(
                    title="Warning Removed",
                    description=f"Removed the warning: `{removed_warning}` from {user.mention}.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Action taken by {interaction.user.display_name}")
                await select_interaction.response.send_message(embed=embed)

            select.callback = select_callback
            view = View()
            view.add_item(select)

            await interaction.response.send_message(
                f"Select a warning to remove from {user.mention}:",
                view=view,
                ephemeral=True
            )
        else:
            embed = discord.Embed(
                title="No Warnings Found",
                description=f"{user.mention} has no warnings.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warnings", description="Show all warnings for a user")
    async def warnings_slash(self, interaction: discord.Interaction, user: discord.Member):
        user_id = str(user.id)

        if user_id in self.warnings and self.warnings[user_id]:
            warning_list = "\n".join(f"{i+1}. {warn}" for i, warn in enumerate(self.warnings[user_id]))

            embed = discord.Embed(
                title=f"Warnings for {user.display_name}",
                description=warning_list,
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title=f"No Warnings for {user.display_name}",
                description=f"{user.mention} has no warnings.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(WarnCog(bot))
