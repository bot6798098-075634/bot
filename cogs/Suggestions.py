import discord
from discord import app_commands
from discord.ext import commands

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_role_id = 1343234687505530902  # Replace with your actual staff role ID
        self.suggestion_channel_id = 1343622169086918758  # Replace with your suggestion channel ID
        self.staff_suggestion_channel_id = 1373704702977376297  # Replace with your staff suggestion channel ID

    @app_commands.command(name="suggestion", description="Submit a suggestion for the bot or server.")
    async def suggestion_slash(self, interaction: discord.Interaction, suggestion: str):
        if not suggestion or len(suggestion) < 10:
            await interaction.response.send_message(
                "Please provide a valid suggestion (at least 10 characters long).",
                ephemeral=True
            )
            return
        
        suggestion_channel = interaction.guild.get_channel(self.suggestion_channel_id)
        if not suggestion_channel:
            await interaction.response.send_message(
                "Suggestion channel not found. Please contact an admin.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="New Suggestion",
            description=suggestion,
            color=discord.Color.green()
        )
        embed.add_field(name="Submitted by", value=str(interaction.user), inline=True)
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        embed.set_footer(text="SWAT Roleplay Community")

        await suggestion_channel.send(embed=embed)
        await interaction.response.send_message(
            "Thank you for your suggestion! It has been submitted for review.",
            ephemeral=True
        )

    @app_commands.command(name="staff_suggestion", description="Submit a staff suggestion for the bot or server.")
    @app_commands.checks.has_role(1343234687505530902)  # Replace with your actual staff role ID
    async def staff_suggestion_slash(self, interaction: discord.Interaction, staff_suggestion: str):
        if len(staff_suggestion.strip()) < 10:
            await interaction.response.send_message(
                "Please provide a valid suggestion (at least 10 characters long).",
                ephemeral=True
            )
            return

        suggestion_channel = interaction.guild.get_channel(self.staff_suggestion_channel_id)
        if not suggestion_channel:
            await interaction.response.send_message(
                "Suggestion channel not found. Please contact an admin.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="New Staff Suggestion",
            description=staff_suggestion,
            color=discord.Color.green()
        )
        embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        embed.set_footer(text="SWAT Roleplay Community")

        await suggestion_channel.send(embed=embed)
        await interaction.response.send_message(
            "Thank you for your suggestion! It has been submitted for review.",
            ephemeral=True
        )

    @staff_suggestion_slash.error
    async def staff_suggestion_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
