import discord
from discord.ext import commands
from discord import app_commands

class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="join_voice_channel", description="Make the bot join your voice channel")
    async def join_voice_channel(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You are not in a voice channel.", ephemeral=True)
            return
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        if voice_client:
            if voice_client.channel.id == channel.id:
                await interaction.response.send_message(f"✅ I'm already in **{channel.name}**.", ephemeral=True)
                return
            else:
                await voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"✅ Joined **{channel.name}**.", ephemeral=True)

    @app_commands.command(name="leave_voice_channel", description="Make the bot leave its current voice channel")
    async def leave_voice_channel(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await interaction.response.send_message("👋 Left the voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)

    @app_commands.command(name="move_to_voice_channel", description="Move the bot to the voice channel of a specified user")
    @app_commands.describe(user="User whose voice channel the bot should join")
    async def move_to_voice_channel(self, interaction: discord.Interaction, user: discord.Member):
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(f"❌ {user.display_name} is not in a voice channel.", ephemeral=True)
            return
        channel = user.voice.channel
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"✅ Moved to **{channel.name}** (user: {user.display_name})", ephemeral=True)

    @app_commands.command(name="disconnect_user", description="Disconnect a user from their voice channel (requires permissions)")
    @app_commands.describe(user="User to disconnect from voice channel")
    async def disconnect_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.move_members:
            await interaction.response.send_message("❌ You don't have permission to disconnect members.", ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(f"❌ {user.display_name} is not in a voice channel.", ephemeral=True)
            return
        try:
            await user.move_to(None)
            await interaction.response.send_message(f"✅ Disconnected {user.display_name} from voice channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to disconnect: {e}", ephemeral=True)

    @app_commands.command(name="mute_user", description="Server mute a user in voice channel (requires permissions)")
    @app_commands.describe(user="User to mute")
    async def mute_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ You don't have permission to mute members.", ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(f"❌ {user.display_name} is not in a voice channel.", ephemeral=True)
            return
        try:
            await user.edit(mute=True)
            await interaction.response.send_message(f"🔇 Muted {user.display_name}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to mute: {e}", ephemeral=True)

    @app_commands.command(name="unmute_user", description="Server unmute a user in voice channel (requires permissions)")
    @app_commands.describe(user="User to unmute")
    async def unmute_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.mute_members:
            await interaction.response.send_message("❌ You don't have permission to unmute members.", ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(f"❌ {user.display_name} is not in a voice channel.", ephemeral=True)
            return
        try:
            await user.edit(mute=False)
            await interaction.response.send_message(f"🔊 Unmuted {user.display_name}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to unmute: {e}", ephemeral=True)

    # Placeholder commands for audio control, extend when adding audio features
    @app_commands.command(name="pause", description="Pause audio playback (if implemented)")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
            return
        voice_client.pause()
        await interaction.response.send_message("⏸️ Paused audio.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume audio playback (if implemented)")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_paused():
            await interaction.response.send_message("❌ Audio is not paused.", ephemeral=True)
            return
        voice_client.resume()
        await interaction.response.send_message("▶️ Resumed audio.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop audio playback and clear queue (if implemented)")
    async def stop(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
            return
        voice_client.stop()
        await interaction.response.send_message("⏹️ Stopped audio.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
