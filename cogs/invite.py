import discord
from discord.ext import commands
from discord import app_commands

class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get the server's invite link")
    async def server_invite_slash(self, interaction: discord.Interaction):
        invites = await interaction.guild.invites()

        if invites:
            invite = invites[0]  # Use the first available invite
            embed = discord.Embed(
                title="Server Invite Link",
                description=f"This is the server invite: {invite.url}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Server Invite Link",
                description="No invites available. Please try again later.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Invite(bot))
