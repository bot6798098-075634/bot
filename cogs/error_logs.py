import discord
from discord.ext import commands
from discord import app_commands

class ErrorLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="error_logs", description="View the latest error logs from the bot.")
    async def error_logs(self, interaction: discord.Interaction):
        file_path = "error.log"

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            await interaction.response.send_message("⚠️ `error.log` not found.", ephemeral=True)
            return

        last_lines = lines[-20:] if len(lines) > 20 else lines
        log_text = "".join(last_lines)

        if len(log_text) > 4000:
            log_text = log_text[-4000:]  # Discord embed limit workaround

        embed = discord.Embed(
            title="🧾 Latest Error Logs",
            description=f"```log\n{log_text}\n```",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorLogs(bot))
