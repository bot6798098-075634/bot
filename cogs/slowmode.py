import discord
from discord import app_commands
from discord.ext import commands

class SlowmodeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="slowmode", description="Set the slowmode duration for a channel")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_slash(self, interaction: discord.Interaction, seconds: int):
        # Check if the bot has permission to manage the channel
        if not interaction.channel.permissions_for(interaction.guild.me).manage_channels:
            await interaction.response.send_message("I don't have permission to manage this channel.", ephemeral=True)
            return

        await interaction.channel.edit(slowmode_delay=seconds)
        embed = discord.Embed(description=f"Slowmode has been set to {seconds} seconds.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(SlowmodeCog(bot))
