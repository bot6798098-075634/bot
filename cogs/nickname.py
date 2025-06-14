import discord
from discord.ext import commands
from discord import app_commands

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nickname", description="Change a user's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def nickname_slash(self, interaction: discord.Interaction, user: discord.Member, new_nickname: str):
        try:
            await user.edit(nick=new_nickname)
            embed = discord.Embed(
                description=f"{user.mention}'s nickname has been changed to **{new_nickname}**.",
                color=discord.Color.green()
            )
        except discord.Forbidden:
            embed = discord.Embed(
                description="I don't have permission to change this user's nickname.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                description=f"An error occurred: {e}",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Nickname(bot))
