import discord
from discord.ext import commands
import re

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # You can load these from a file or database instead
        self.blocked_words = {"badword1", "badword2", "anotherbadword"}  # lowercase words blocked
        self.custom_blocked = {"blockedphrase", "somebadword"}  # additional custom blocked words
        self.allowed_words = {"allowedword", "goodword"}  # whitelist words that bypass block
        
        # Simple regex for detecting links (http/https, www, discord invite, etc)
        self.link_regex = re.compile(
            r"(https?://\S+|www\.\S+|discord\.gg/\S+|discordapp\.com/invite/\S+)", re.IGNORECASE
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return  # ignore bots

        content = message.content.lower()

        # Check for allowed words (whitelist) first - if any allowed word is present, skip blocking
        if any(allowed_word in content for allowed_word in self.allowed_words):
            return

        # Check links - block if message contains link
        if self.link_regex.search(content):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, posting links is not allowed here.",
                    delete_after=10
                )
            except discord.Forbidden:
                # bot doesn't have permission to delete/send messages
                pass
            return

        # Check for blocked words (blocked_words + custom_blocked)
        all_blocked = self.blocked_words.union(self.custom_blocked)
        if any(bad_word in content for bad_word in all_blocked):
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, your message contains blocked words and was removed.",
                    delete_after=10
                )
            except discord.Forbidden:
                pass
            return

    # Optional slash commands to manage blocked/custom/allowed words could be added here

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
