import discord
from discord.ext import commands
from discord import app_commands

OWNER_ID = 1276264248095412387  # Replace with your actual Discord user ID

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shutdown", description="Shut down the bot (owner only)")
    async def shutdown(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ You do not have permission to shut down the bot.", ephemeral=True)
            return

        await interaction.response.send_message("🛑 Shutting down the bot... Goodbye!", ephemeral=True)
        await self.bot.close()

async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
