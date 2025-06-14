import discord
from discord import app_commands
from discord.ext import commands

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="afk", description="Set yourself as AFK")
    @app_commands.describe(reason="Optional reason for going AFK")
    async def afk_slash(self, interaction: discord.Interaction, reason: str = "AFK"):
        afk_role = discord.utils.get(interaction.guild.roles, name="AFK")

        if not afk_role:
            afk_role = await interaction.guild.create_role(name="AFK", reason="AFK system initialization")

            for channel in interaction.guild.channels:
                try:
                    await channel.set_permissions(afk_role, speak=False, send_messages=False)
                except Exception:
                    continue

        if afk_role in interaction.user.roles:
            await interaction.response.send_message("You're already marked as AFK.", ephemeral=True)
            return

        await interaction.user.add_roles(afk_role, reason=reason)

        embed = discord.Embed(
            description=f"{interaction.user.mention} is now AFK: {reason}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unafk", description="Remove yourself from AFK")
    async def unafk_slash(self, interaction: discord.Interaction):
        afk_role = discord.utils.get(interaction.guild.roles, name="AFK")

        if not afk_role or afk_role not in interaction.user.roles:
            await interaction.response.send_message("You're not currently marked as AFK.", ephemeral=True)
            return

        await interaction.user.remove_roles(afk_role)

        embed = discord.Embed(
            description=f"{interaction.user.mention} is no longer AFK",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))
