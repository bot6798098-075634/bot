import discord
from discord.ext import commands
from discord import app_commands
import json
import os

LOGS_CONFIG_FILE = 'logs_config.json'

def load_logs_config():
    if os.path.exists(LOGS_CONFIG_FILE):
        with open(LOGS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_logs_config(data):
    with open(LOGS_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_logs_config()

    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        webhook_url = self.config.get(str(guild.id))
        if webhook_url:
            webhook = discord.Webhook.from_url(webhook_url, session=self.bot.http._HTTPClient__session)
            await webhook.send(embed=embed, username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url)

    @app_commands.command(name="logs_set", description="Set the logging channel")
    @app_commands.describe(channel="Channel to log events in")
    @app_commands.checks.has_permissions(manage_guild=True)  # Optional: only allow admins
    async def logs_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not channel.permissions_for(interaction.guild.me).manage_webhooks:
            await interaction.response.send_message("❌ I need Manage Webhooks permission in that channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        webhooks = await channel.webhooks()
        webhook = next((w for w in webhooks if w.user == self.bot.user), None)

        if webhook is None:
            webhook = await channel.create_webhook(name=self.bot.user.name, avatar=await self.bot.user.display_avatar.read())

        self.config[str(interaction.guild.id)] = webhook.url
        save_logs_config(self.config)

        embed = discord.Embed(
            title="✅ Logging Enabled",
            description=f"Logs will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await webhook.send(embed=embed, username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url)
        await interaction.followup.send(f"✅ Logs set in {channel.mention}", ephemeral=True)

    # --- Event Listeners ---

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(title="👤 Member Joined", description=f"{member.mention} joined.", color=discord.Color.green())
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(title="👤 Member Left", description=f"{member.mention} left or was kicked.", color=discord.Color.red())
        embed.set_footer(text=f"ID: {member.id}")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(title="✏️ Nickname Changed", color=discord.Color.orange())
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            embed.set_footer(text=f"{after} • ID: {after.id}")
            await self.send_log(after.guild, embed)

        # Roles changed
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            embed = discord.Embed(title="🎭 Roles Updated", color=discord.Color.blurple())
            if added:
                embed.add_field(name="Added", value=", ".join(r.mention for r in added), inline=False)
            if removed:
                embed.add_field(name="Removed", value=", ".join(r.mention for r in removed), inline=False)
            embed.set_footer(text=f"{after} • ID: {after.id}")
            await self.send_log(after.guild, embed)

        # Timeout change
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until:
                title = "🔕 Member Timed Out"
                color = discord.Color.dark_red()
            else:
                title = "🔔 Timeout Removed"
                color = discord.Color.green()
            embed = discord.Embed(title=title, description=f"{after.mention}", color=color)
            await self.send_log(after.guild, embed)

        # Server Boost (premium_since change)
        if before.premium_since is None and after.premium_since is not None:
            embed = discord.Embed(title="🚀 Server Boost", description=f"{after.mention} just boosted the server!", color=discord.Color.purple())
            await self.send_log(after.guild, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(title="🔨 Banned", description=f"{user} was banned", color=discord.Color.red())
        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(title="♻️ Unbanned", description=f"{user} was unbanned", color=discord.Color.green())
        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:
            embed = discord.Embed(title="🗑️ Message Deleted", description=f"In {message.channel.mention}", color=discord.Color.red())
            embed.add_field(name="Author", value=message.author.mention)
            embed.add_field(name="Content", value=message.content or "*No content*", inline=False)
            await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and before.content != after.content:
            embed = discord.Embed(title="✏️ Message Edited", description=f"In {before.channel.mention}", color=discord.Color.orange())
            embed.add_field(name="Author", value=before.author.mention)
            embed.add_field(name="Before", value=before.content or "*Empty*", inline=False)
            embed.add_field(name="After", value=after.content or "*Empty*", inline=False)
            await self.send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(title="📁 Channel Created", description=f"{channel.mention} was created", color=discord.Color.green())
            await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(title="🗑️ Channel Deleted", description=f"#{channel.name} was deleted", color=discord.Color.red())
        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        embed = discord.Embed(title="🔧 Channel Updated", color=discord.Color.blue())
        changed = False

        if before.name != after.name:
            embed.add_field(name="Name", value=f"`{before.name}` ➜ `{after.name}`", inline=False)
            changed = True

        if hasattr(before, "topic") and before.topic != after.topic:
            embed.add_field(name="Topic", value=f"`{before.topic}` ➜ `{after.topic}`", inline=False)
            changed = True

        if hasattr(before, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            embed.add_field(name="Slowmode", value=f"`{before.slowmode_delay}s` ➜ `{after.slowmode_delay}s`", inline=False)
            changed = True

        if changed:
            await self.send_log(before.guild, embed)

async def setup(bot):
    await bot.add_cog(LogsCog(bot))
