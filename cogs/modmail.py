import discord
from discord.ext import commands
from discord import app_commands
import re
import io
import logging

logger = logging.getLogger(__name__)

class Modmail(commands.Cog):
    """
    A Modmail cog that handles user DMs to create modmail threads in a guild,
    with staff interaction through slash commands and buttons.
    """

    GUILD_ID = 1343179590247645205
    CATEGORY_ID = 1368337231508406322
    STAFF_ROLE_IDS = {1346578198749511700}
    TRANSCRIPT_LOG_CHANNEL = 1381267054354632745
    STAFF_ROLE_PING = "<@&1346578198749511700>"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_threads = {}  # Maps user_id -> channel_id
        self.claimed_by = {}      # Maps user_id -> staff_id

    def _sanitize_name(self, name: str) -> str:
        """Sanitize username to safe channel name format."""
        return re.sub(r"[^a-zA-Z0-9]", "-", name.lower())[:90]

    async def _get_or_create_thread(self, user: discord.User) -> discord.TextChannel:
        """Get an existing modmail thread or create a new one for the user."""
        guild = self.bot.get_guild(self.GUILD_ID)
        if guild is None:
            raise RuntimeError("Guild not found")

        category = guild.get_channel(self.CATEGORY_ID)
        if category is None:
            raise RuntimeError("Category not found")

        # Check existing thread with topic = user ID
        existing = discord.utils.get(category.text_channels, topic=f"ID:{user.id}")
        if existing:
            return existing

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
        }

        channel_name = f"modmail-{self._sanitize_name(user.name)}"
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"ID:{user.id}",
            overwrites=overwrites
        )
        self.active_threads[user.id] = channel.id
        await channel.send(f"{self.STAFF_ROLE_PING} 📬 New modmail opened by {user.mention} (`{user.id}`)")
        logger.info(f"Created modmail thread {channel_name} for user {user} ({user.id})")
        return channel

    class ConfirmView(discord.ui.View):
        def __init__(self, cog, user, content):
            super().__init__(timeout=60)
            self.cog = cog
            self.user = user
            self.content = content

        @discord.ui.button(label="📨 Send to Staff", style=discord.ButtonStyle.green)
        async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != self.user:
                return await interaction.response.send_message("This prompt is not for you.", ephemeral=True)

            try:
                channel = await self.cog._get_or_create_thread(self.user)
            except Exception as e:
                logger.error(f"Failed to get or create modmail thread: {e}")
                return await interaction.response.send_message("⚠️ Could not open modmail thread.", ephemeral=True)

            embed = discord.Embed(
                title="📩 New Modmail Message",
                description=self.content,
                color=discord.Color.blue()
            )
            embed.set_author(name=str(self.user), icon_url=self.user.display_avatar.url)
            embed.set_footer(text=f"User ID: {self.user.id}")

            await channel.send(embed=embed)
            await interaction.response.edit_message(content="✅ Message sent to staff.", view=None)

            try:
                await self.user.send("🔒 Use the button below to close this thread when done.", view=self.cog.CloseView(self.cog, self.user.id))
            except Exception:
                logger.warning(f"Could not send close button DM to user {self.user.id}")

    class CloseView(discord.ui.View):
        def __init__(self, cog, user_id):
            super().__init__(timeout=None)
            self.cog = cog
            self.user_id = user_id

        @discord.ui.button(label="🔒 Close Thread", style=discord.ButtonStyle.red)
        async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
            channel_id = self.cog.active_threads.get(self.user_id)
            if not channel_id:
                return await interaction.response.send_message("Thread not found or already closed.", ephemeral=True)

            guild = self.cog.bot.get_guild(self.cog.GUILD_ID)
            if guild is None:
                return await interaction.response.send_message("Guild not found.", ephemeral=True)

            channel = guild.get_channel(channel_id)
            if channel is None:
                return await interaction.response.send_message("Channel not found.", ephemeral=True)

            await channel.send("🛑 User closed the thread.")
            await self.cog._send_transcript(channel, self.user_id)

            self.cog.active_threads.pop(self.user_id, None)
            await interaction.response.send_message("✅ Thread closed. Thank you!")

    async def _send_transcript(self, channel: discord.TextChannel, user_id: int):
        """Send a transcript of the modmail conversation to logs and user."""
        lines = []
        async for msg in channel.history(limit=None, oldest_first=True):
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{time_str}] {msg.author}: {msg.content}")

        transcript = "\n".join(lines)
        transcript_file = discord.File(io.BytesIO(transcript.encode()), filename="transcript.txt")

        log_channel = self.bot.get_channel(self.TRANSCRIPT_LOG_CHANNEL)
        user = await self.bot.fetch_user(user_id)

        if log_channel:
            await log_channel.send(f"📝 Transcript for user `{user}`", file=transcript_file)

        try:
            await user.send("📄 Here's the transcript of your modmail session:", file=transcript_file)
        except Exception:
            logger.warning(f"Could not DM transcript to user {user_id}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and non-DMs
        if message.author.bot:
            return

        if message.guild is None:
            # User DM
            user = message.author
            channel = None

            channel_id = self.active_threads.get(user.id)
            if channel_id:
                guild = self.bot.get_guild(self.GUILD_ID)
                if guild:
                    channel = guild.get_channel(channel_id)

            if channel is None:
                # Prompt user to confirm sending to staff
                await message.channel.send(
                    embed=discord.Embed(
                        title="Send to Staff?",
                        description=message.content,
                        color=discord.Color.orange()
                    ),
                    view=self.ConfirmView(self, user, message.content)
                )
                return

            embed = discord.Embed(description=message.content, color=discord.Color.green())
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)
            await channel.send(embed=embed)

        else:
            # Guild message
            topic = message.channel.topic
            if topic and topic.startswith("ID:") and message.author.id != self.bot.user.id:
                try:
                    user_id = int(topic.replace("ID:", ""))
                    user = await self.bot.fetch_user(user_id)

                    embed = discord.Embed(description=message.content, color=discord.Color.purple())
                    embed.set_author(name=f"Staff: {message.author}")

                    await user.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error sending staff reply to user DM: {e}")
                    await message.channel.send(f"❌ Could not message user: {e}")

    # Slash commands - registered globally or per guild
    @app_commands.command(name="claim", description="Claim this modmail thread.")
    @app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
    async def claim(self, interaction: discord.Interaction):
        topic = interaction.channel.topic
        if not topic or not topic.startswith("ID:"):
            return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

        user_id = int(topic.replace("ID:", ""))
        user = await self.bot.fetch_user(user_id)
        self.claimed_by[user_id] = interaction.user.id
        await interaction.response.send_message(f"✅ Claimed by {interaction.user.mention}")

        try:
            await user.send(f"👮 Your modmail was claimed by {interaction.user.name}.")
        except Exception:
            logger.warning(f"Could not DM claim notice to user {user_id}")

    @app_commands.command(name="close", description="Close and archive this thread.")
    @app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
    async def close(self, interaction: discord.Interaction):
        topic = interaction.channel.topic
        if not topic or not topic.startswith("ID:"):
            return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

        user_id = int(topic.replace("ID:", ""))
        await interaction.response.send_message("🔒 Closing and sending transcript...")
        await interaction.channel.send("🔒 Closed by staff.")

        try:
            user = await self.bot.fetch_user(user_id)
            await user.send("🔒 Your modmail thread has been closed by staff.")
        except Exception:
            logger.warning(f"Could not DM close notice to user {user_id}")

        await self._send_transcript(interaction.channel, user_id)
        self.active_threads.pop(user_id, None)

    @app_commands.command(name="delete", description="Delete this modmail channel.")
    @app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
    async def delete(self, interaction: discord.Interaction):
        await interaction.response.send_message("🗑 Deleting channel...", ephemeral=True)
        await interaction.channel.delete()

    @app_commands.command(name="transcript", description="Get transcript of this thread.")
    @app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
    async def transcript(self, interaction: discord.Interaction):
        topic = interaction.channel.topic
        if not topic or not topic.startswith("ID:"):
            return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

        user_id = int(topic.replace("ID:", ""))
        await self._send_transcript(interaction.channel, user_id)
        await interaction.response.send_message("📄 Transcript sent.")

    async def cog_load(self):
        # Sync commands to guild for faster registration (optional)
        guild = discord.Object(id=self.GUILD_ID)
        self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)

async def setup(bot: commands.Bot):
    await bot.add_cog(Modmail(bot))
