import discord
from discord import app_commands
from discord.ext import commands

class EmbedCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Make an advanced embed")
    @app_commands.describe(
        title="The title of the embed",
        description="The description of the embed",
        color="The color of the embed in hex (e.g., #3498db)",
        thumbnail_url="URL for a thumbnail image (optional)",
        image_url="URL for a main image (optional)",
        footer="Text to show in the footer (optional)",
        author="Author name to show (optional)"
    )
    async def embed_slash(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        color: str = "#3498db",
        thumbnail_url: str = None,
        image_url: str = None,
        footer: str = None,
        author: str = None
    ):
        try:
            embed_color = discord.Color(int(color.lstrip("#"), 16))
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid color! Please use a hex color code like `#3498db`.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title=title, description=description, color=embed_color)

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        if image_url:
            embed.set_image(url=image_url)
        if footer:
            embed.set_footer(text=footer)
        if author:
            embed.set_author(name=author)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCreator(bot))
