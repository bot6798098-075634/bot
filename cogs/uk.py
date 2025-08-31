import discord
from discord.ext import commands
from discord import app_commands
from utils.checks import is_owner
from utils.emojis import emojis

ANNOUNCEMENT = f"""-# {emojis['ping_emoji']} @everyone

# {emojis['an_emoji']} Important Announcement

Hello everyone! I have an important news regarding ER:LC and Roblox access:

### {emojis['help_emoji']} **What’s happening:**

{emojis['dot_emoji']} Roblox has been **banned in the UK**.
{emojis['dot_emoji']} This means I am **currently unable to join ER:LC** or access any Roblox-related content.

### 🫵 **What this means for you:**  

{emojis['dot_emoji']} Can continue sessions and other stuff if <@&1343234687505530902> can do sessions.
{emojis['dot_emoji']} As of right now I do not know what to do.

Thank you.

**Signed:** <@1276264248095412387>
"""

class UK(commands.Cog):
    """Owner-only UK announcement commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------- Prefix Command ----------------
    @commands.command(name="uk")
    @commands.is_owner()
    async def uk_prefix(self, ctx: commands.Context):
        await ctx.send(ANNOUNCEMENT)

    # Prefix error handling
    @uk_prefix.error
    async def uk_prefix_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.NotOwner):
            await ctx.message.add_reaction(failed_emoji)

    # ---------------- Slash Command ----------------
    @app_commands.command(name="uk", description="Owner only.")
    @is_owner()
    async def uk_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(ANNOUNCEMENT)

    # Slash error handling
    @uk_slash.error
    async def uk_slash_error(self, interaction: discord.Interaction, error):
        from discord.app_commands import AppCommandError
        if isinstance(error, AppCommandError):
            await interaction.response.send_message(
                "❌ Owner only command.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UKAnnouncement(bot))