import discord
from discord.ext import commands
from discord import app_commands

class ServerIcon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="servericon", description="Display the server's icon")
    async def servericon_slash(self, interaction: discord.Interaction):
        if interaction.guild.icon:
            embed = discord.Embed(
                title=f"{interaction.guild.name} Server Icon",
                color=discord.Color.blue()
            )
            embed.set_image(url=interaction.guild.icon.url)
        else:
            embed = discord.Embed(
                description="This server has no icon.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerIcon(bot))
