# ========================= Import =========================

import discord
import asyncio
import random
import requests
import sys
import subprocess
import os
import logging
from discord import Embed
import re
import json
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Select
from discord.utils import get
from discord.raw_models import RawReactionActionEvent
import aiohttp
from datetime import UTC
from collections import defaultdict, deque
from discord.ui import Button, View
from discord import app_commands, ui
import re, io
import datetime
from datetime import datetime
from threading import Thread
from datetime import datetime, timezone
from datetime import timezone
import typing
import atexit
import copy
from dotenv import load_dotenv
from keep_alive import keep_alive

# ========================= Other =========================

if __name__ == "__main__":
    keep_alive()  # starts the Flask server to keep the app alive
    # your other bot or app code here

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UTC = timezone.utc

SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blue()
intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True
intents = discord.Intents.all()

kill_tracker = defaultdict(lambda: deque())
bot = commands.Bot(command_prefix=".", intents=intents)

tree = bot.tree
events = []

OWNER_ID = 1276264248095412387

session: aiohttp.ClientSession | None = None

erlc_group = app_commands.Group(name="erlc", description="ERLC related commands")
discord_group = app_commands.Group(name="discord", description="Discord-related commands")
error_group = app_commands.Group(name="error", description="Error logs and diagnostics")
server_group = app_commands.Group(name="server", description="Server-related commands")
user_group = app_commands.Group(name="user", description="User tools and utilities")
role_group = app_commands.Group(name="role", description="Role management commands")

# Register groups once (DO NOT register them in on_ready)
bot.tree.add_command(erlc_group)
bot.tree.add_command(discord_group)
bot.tree.add_command(error_group)
bot.tree.add_command(server_group)
bot.tree.add_command(user_group)
bot.tree.add_command(role_group)

# ========================= Bot on_ready =========================

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        await bot.tree.sync(guild=discord.Object(id=1343179590247645205))  # Optional: Your specific guild ID
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    bot.start_time = datetime.now(timezone.utc)

    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()

    # Start background tasks
    try:
        join_leave_log_task.start()
        kill_log_task.start()
        process_joins_loop.start()
        check_log_commands.start()
        update_vc_status.start()
        check_staff_livery.start()
    except Exception as e:
        print(f"Error starting background tasks: {e}")

    # Set bot presence
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    print(f"{bot.user} has connected to Discord and is watching over the server.")
    print("-----------------------------------------------------------------------")

# ========================= Emojis =========================

time_emoji = "<:time:1387841153491271770>"
tick_emoji = "<:tick:1383796116763709532>"
error_emoji = "<:error:1383587321294884975>"
ping_emoji = "<:ping:1381073968873607229>"
logo_emoji = "<:logo:1322987575375429662>"
pong_emoji = "<:pong:1387845465315348480>"
failed_emoji = "<:failed:1387853598733369435>"
note_emoji = "<:note:1387865341773873302>"
clipboard_emoji = "<:clipboard:1387890654868410408>"
owner_emoji = "<:owner:1387900933006164160>" 

# ========================= Role IDs =========================

staff_role_id = "1343234687505530902"
mod_role_id = "1346576470360850432"
admin_role_id = "1346577013774880892"
superviser_role_id = "1346577369091145728"
management_role_id = "1346578020747575368"
ia_role_id = "1371537163522543647"
ownership_role_id = "1346578250381656124"
session_manager_role_id = "1374839922976100472"
staff_trainer_role_id = "1377794070440837160"
afk_role_id = "1355829296085729454"
event_role_id = "1346740470272757760"
staff_help_role_id = "1370096425282830437" 

# ========================= Slash commands and prefix commands =========================

async def send_error(ctx_or_interaction, description="If you continue to encounter errors, please notify the owner.", ephemeral=False):
    embed = discord.Embed(
        title=f"{error_emoji} Error!",
        description=description,
        color=0xFF1414
    )
    # Check if ctx_or_interaction is a commands.Context (prefix command) or discord.Interaction (slash command)
    if hasattr(ctx_or_interaction, "response"):  # Interaction
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=ephemeral)
    else:  # Context
        await ctx_or_interaction.send(embed=embed)

# ------------------------ ping slash command ------------------------

@tree.command(name="ping", description="Check bot's latency and uptime")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # in ms
    now = datetime.now(timezone.utc)
    uptime_duration = now - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

    embed = discord.Embed(
        title=f"{logo_emoji} SWAT Roleplay Community",
        description=(
            "Information about the bot status\n"
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ),
        color=discord.Color.blue()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")
    await interaction.response.send_message(embed=embed)

# ------------------------ ping prefix command ------------------------

@bot.command(name="ping")
async def ping_prefix(ctx):
    latency = round(bot.latency * 1000)  # in ms
    now = datetime.now(timezone.utc)
    uptime_duration = now - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

    embed = discord.Embed(
        title="SWAT Roleplay Community",
        description=(
            "Information about the bot status\n"
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ),
        color=discord.Color.blue()
    )

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")
    await ctx.send(embed=embed)




@bot.tree.command(name="emojis", description="Display all bot emojis")
async def emojis(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 Bot Emojis",
        description=(
            f"{time_emoji} `time`\n"
            f"{tick_emoji} `tick`\n"
            f"{error_emoji} `error`\n"
            f"{ping_emoji} `ping`\n"
            f"{pong_emoji} `pong`\n"
            f"{logo_emoji} `logo`\n"
            f"{failed_emoji} `failed`\n"
            f"{note_emoji} `note`\n"
            f"{clipboard_emoji} `clipboard`\n"
            f"{owner_emoji} `owner`\n"
        ),
        color=0x1499ff
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")
    await interaction.response.send_message(embed=embed)










# ------------------------ Say slash command ------------------------

@tree.command(name="say", description="Make the bot say something anonymously")
@app_commands.describe(message="The message for the bot to say")
async def say_slash(interaction: discord.Interaction, message: str):
    staff_role = interaction.guild.get_role(staff_role_id)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message(f"{failed_emoji} You don't have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message(f"{tick_emoji} Message sent!", ephemeral=True)
    await interaction.channel.send(message)

# ------------------------ Say prefix command ------------------------

@bot.command(name="say")
@commands.has_role(staff_role_id)
async def say_prefix(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await ctx.send(message)

@say_prefix.error
async def say_prefix_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        try:
            # React with your custom emoji (must be on the server where command was used)
            await ctx.message.add_reaction(failed_emoji)
        except discord.Forbidden:
            pass  # No permission to react or add emoji

# ------------------------ Embed Slash Command ------------------------

@tree.command(name="embed", description="Make a custom embed like the say command")
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
    interaction: discord.Interaction,
    title: str,
    description: str,
    color: str = "#3498db",
    thumbnail_url: str = None,
    image_url: str = None,
    footer: str = None,
    author: str = None
):
    # Check for staff role
    staff_role = interaction.guild.get_role(staff_role_id)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message(
            f"{failed_emoji} You don't have permission to use this command.",
            ephemeral=True
        )
        return

    # Validate hex color
    try:
        embed_color = discord.Color(int(color.lstrip("#"), 16))
    except ValueError:
        await interaction.response.send_message(
            f"{error_emoji} Invalid color! Please use a hex code like `#3498db`.",
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

# ------------------------ Embed Prefix Command ------------------------

@bot.command(name="embed")
async def embed_prefix(ctx, *, args=None):
    staff_role = ctx.guild.get_role(staff_role_id)
    if staff_role not in ctx.author.roles:
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.Forbidden:
            pass
        return

    # Basic check: require at least title and description
    # args is a string of all arguments after command
    # We'll attempt to split it by some separator, e.g. " | "
    # Or you can require the user to run slash command if no args
    
    if not args:
        await send_wrong_format_message(ctx)
        return

    # For simplicity, expect the user to separate fields by " | "
    # like: Title | Description | #color | thumbnail | image | footer | author
    parts = [part.strip() for part in args.split("|")]

    if len(parts) < 2:
        await send_wrong_format_message(ctx)
        return

    title = parts[0]
    description = parts[1]
    color = parts[2] if len(parts) > 2 else "#3498db"
    thumbnail_url = parts[3] if len(parts) > 3 else None
    image_url = parts[4] if len(parts) > 4 else None
    footer = parts[5] if len(parts) > 5 else None
    author = parts[6] if len(parts) > 6 else None

    try:
        embed_color = discord.Color(int(color.lstrip("#"), 16))
    except ValueError:
        await ctx.send(f"{error_emoji} Invalid color! Please use a hex color code like `#3498db`.")
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

    await ctx.send(embed=embed)


async def send_wrong_format_message(ctx):
    # Build the embed explaining the proper usage, and ping the user
    embed = discord.Embed(
        title="Incorrect command usage",
        description=(
            f"-# {ping_emoji} {ctx.author.mention}\n\n"
            "Please use the slash command `/embed` for this.\n\n"
            "Example usage:\n"
            "`/embed title:\"My Title\" description:\"My description\" color:\"#3498db\"`\n\n"
            "Optional fields: thumbnail_url, image_url, footer, author"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="This message will auto-delete in 10 seconds.")

    msg = await ctx.send(embed=embed)

    # Delete message after 10 seconds
    await msg.delete(delay=10)

# ------------------------ Slowmode slash command ------------------------

@tree.command(name="slowmode", description="Set the slowmode duration for a channel")
@app_commands.describe(seconds="Duration of slowmode in seconds")
async def slowmode_slash(interaction: discord.Interaction, seconds: int):
    staff_role = interaction.guild.get_role(staff_role_id)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message(
            f"{failed_emoji} You don't have permission to use this command.",
            ephemeral=True
        )
        return

    await interaction.channel.edit(slowmode_delay=seconds)

    embed = discord.Embed(
        description=f"{time_emoji} Slowmode has been set to `{seconds}` seconds.",
        color=discord.Color.green()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ Slowmode prefix command ------------------------

@bot.command(name="slowmode")
async def slowmode_prefix(ctx, seconds: int):
    staff_role = ctx.guild.get_role(staff_role_id)
    if staff_role not in ctx.author.roles:
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.Forbidden:
            pass
        return

    await ctx.channel.edit(slowmode_delay=seconds)

    embed = discord.Embed(
        description=f"{time_emoji} Slowmode has been set to `{seconds}` seconds.",
        color=discord.Color.green()
    )

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ Uptime Slash Command ------------------------

@tree.command(name="uptime", description="Show how long the bot has been running.")
async def uptime_slash(interaction: discord.Interaction):
    now = discord.utils.utcnow()
    uptime_seconds = int((now - bot.start_time).total_seconds())

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    def format_time(unit, label):
        return f"{unit} {label}{'s' if unit != 1 else ''}"

    uptime_parts = [
        format_time(days, "day"),
        format_time(hours, "hour"),
        format_time(minutes, "minute"),
        format_time(seconds, "second")
    ]

    uptime_str = ", ".join(part for part in uptime_parts if not part.startswith("0"))

    embed = discord.Embed(
        title=f"{time_emoji} Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=discord.Color.blue()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ Uptime Prefix Command ------------------------

@bot.command(name="uptime")
async def uptime_prefix(ctx):
    now = discord.utils.utcnow()
    uptime_seconds = int((now - bot.start_time).total_seconds())

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    def format_time(unit, label):
        return f"{unit} {label}{'s' if unit != 1 else ''}"

    uptime_parts = [
        format_time(days, "day"),
        format_time(hours, "hour"),
        format_time(minutes, "minute"),
        format_time(seconds, "second")
    ]

    uptime_str = ", ".join(part for part in uptime_parts if not part.startswith("0"))

    embed = discord.Embed(
        title=f"{time_emoji} Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=discord.Color.blue()
    )

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ AFK Slash Command ------------------------

afk_reasons = {}  # user_id -> reason

@tree.command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Optional reason for going AFK")
async def afk_slash(interaction: discord.Interaction, reason: str = "AFK"):

    afk_role = interaction.guild.get_role(afk_role_id)
    if not afk_role:
        await interaction.response.send_message("AFK role not found on this server.", ephemeral=True)
        return

    if afk_role in interaction.user.roles:
        await interaction.response.send_message("You're already marked as AFK.", ephemeral=True)
        return

    await interaction.user.add_roles(afk_role, reason=reason)
    afk_reasons[interaction.user.id] = reason

    embed = discord.Embed(
        description=f"{interaction.user.mention} is now AFK: {reason}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ AFK Prefix Command ------------------------

@bot.command(name="afk")
async def afk_prefix(ctx, *, reason: str = "AFK"):

    afk_role = ctx.guild.get_role(afk_role_id)
    if not afk_role:
        await ctx.send("AFK role not found on this server.")
        return

    if afk_role in ctx.author.roles:
        await ctx.send("You're already marked as AFK.")
        return

    await ctx.author.add_roles(afk_role, reason=reason)
    afk_reasons[ctx.author.id] = reason

    embed = discord.Embed(
        description=f"{ctx.author.mention} is now AFK: {reason}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ AFK Mention Detection ------------------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    afk_role = message.guild.get_role(afk_role_id)
    if not afk_role:
        return

    # Check all mentioned users
    for user in message.mentions:
        if afk_role in user.roles:
            reason = afk_reasons.get(user.id, "AFK")
            embed = discord.Embed(
                description=(
                    f"{note_emoji} Please do not ping {user.mention}.\n"
                    f"They are currently AFK: {reason}"
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            if message.guild and message.guild.icon:
                embed.set_thumbnail(url=message.guild.icon.url)
            embed.set_footer(text="SWAT Roleplay Community")

            await message.channel.send(embed=embed)
            break  # send once per message

    await bot.process_commands(message)  # important to allow commands still to work

# ------------------------ UnAFK Slash Command ------------------------

@tree.command(name="unafk", description="Remove your AFK status")
async def unafk_slash(interaction: discord.Interaction):
    afk_role = interaction.guild.get_role(afk_role_id)
    if not afk_role:
        await interaction.response.send_message(f"{error_emoji} AFK role not found on this server please open a ticket.", ephemeral=True)
        return

    if afk_role not in interaction.user.roles:
        await interaction.response.send_message(f"{error_emoji} You are not marked as AFK.", ephemeral=True)
        return

    await interaction.user.remove_roles(afk_role, reason="User removed AFK status")
    afk_reasons.pop(interaction.user.id, None)

    embed = discord.Embed(
        description=f"{interaction.user.mention} is no longer AFK.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ UnAFK Prefix Command ------------------------

@bot.command(name="unafk")
async def unafk_prefix(ctx):
    afk_role = ctx.guild.get_role(afk_role_id)
    if not afk_role:
        await ctx.send(f"{error_emoji} AFK role not found on this server please open a ticket.")
        return

    if afk_role not in ctx.author.roles:
        await ctx.send(f"{error_emoji} You are not marked as AFK.")
        return

    await ctx.author.remove_roles(afk_role, reason="User removed AFK status")
    afk_reasons.pop(ctx.author.id, None)

    embed = discord.Embed(
        description=f"{ctx.author.mention} is no longer AFK.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ User Info Slash Command ------------------------

@user_group.command(name="info", description="Get information about a user.")
@app_commands.describe(member="The member to get info about")
async def userinfo_slash(interaction: discord.Interaction, member: discord.Member):
    roles = [role.mention for role in member.roles if role != member.guild.default_role]
    roles_display = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(
        title=f"👤 User Information: {member}",
        color=member.color if member.color.value else discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=member.avatar.url if member.avatar else discord.Embed.Empty)

    embed.add_field(name=f"{clipboard_emoji} Username", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="🆔 User ID", value=member.id, inline=True)
    embed.add_field(name="📆 Account Created", value=member.created_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
    embed.add_field(name="📥 Joined Server", value=member.joined_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
    embed.add_field(name="🎭 Roles", value=roles_display, inline=False)
    embed.add_field(name=f"{pong_emoji} Status", value=str(member.status).title(), inline=True)
    embed.add_field(name="🤖 Bot?", value="Yes" if member.bot else "No", inline=True)

    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)  # optional guild icon thumbnail override
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ User Info Prefix Command ------------------------

@bot.command(name="userinfo")
async def userinfo_prefix(ctx, member: discord.Member = None):
    member = member or ctx.author

    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
    roles_display = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(
        title=f"👤 User Information: {member}",
        color=member.color if member.color.value else discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=member.avatar.url if member.avatar else discord.Embed.Empty)

    embed.add_field(name="📝 Username", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="🆔 User ID", value=member.id, inline=True)
    embed.add_field(name="📆 Account Created", value=member.created_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
    embed.add_field(name="📥 Joined Server", value=member.joined_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
    embed.add_field(name="🎭 Roles", value=roles_display, inline=False)
    embed.add_field(name="📶 Status", value=str(member.status).title(), inline=True)
    embed.add_field(name="🤖 Bot?", value="Yes" if member.bot else "No", inline=True)

    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)  # optional guild icon thumbnail override
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# Alias to allow "user info" prefix command:

@bot.command(name="user")
async def user_prefix(ctx, *, arg=None):
    if arg and arg.lower().startswith("info"):
        # Try to get member mention or name after 'info'
        parts = arg.split(maxsplit=1)
        member = None
        if len(parts) > 1:
            try:
                member = await commands.MemberConverter().convert(ctx, parts[1])
            except commands.BadArgument:
                await ctx.send("Member not found.")
                return
        await ctx.invoke(bot.get_command("userinfo"), member=member)
    else:
        await ctx.send("Usage: `user info [member]`")

# ------------------------ Role Info Slash Command ------------------------

@role_group.command(name="info", description="Get information about a specific role")
@app_commands.describe(role="The role to get info about")
async def roleinfo_slash(interaction: discord.Interaction, role: discord.Role):
    permissions = [perm[0].replace("_", " ").title() for perm in role.permissions if perm[1]]
    permissions_display = ", ".join(permissions) if permissions else "No permissions"

    embed = discord.Embed(
        title=f"Role Info for {role.name}",
        color=role.color if role.color.value else discord.Color.default()
    )

    embed.add_field(name="Role Name", value=role.name, inline=False)
    embed.add_field(name="Created At", value=role.created_at.strftime("%B %d, %Y"), inline=False)
    embed.add_field(name="Position", value=role.position, inline=False)
    embed.add_field(name="Permissions", value=permissions_display, inline=False)

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)



# ------------------------ Role Info Prefix Command ------------------------

@bot.command(name="roleinfo")
async def roleinfo_prefix(ctx, *, role: discord.Role):
    permissions = [perm[0].replace("_", " ").title() for perm in role.permissions if perm[1]]
    permissions_display = ", ".join(permissions) if permissions else "No permissions"

    embed = discord.Embed(
        title=f"Role Info for {role.name}",
        color=role.color if role.color.value else discord.Color.default()
    )

    embed.add_field(name="Role Name", value=role.name, inline=False)
    embed.add_field(name="Created At", value=role.created_at.strftime("%B %d, %Y"), inline=False)
    embed.add_field(name="Position", value=role.position, inline=False)
    embed.add_field(name="Permissions", value=permissions_display, inline=False)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# Alias to allow "role info" prefix command

@bot.command(name="role")
async def role_prefix(ctx, *, arg=None):
    if arg and arg.lower().startswith("info"):
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            await ctx.send("Usage: `role info <role>`")
            return
        try:
            role = await commands.RoleConverter().convert(ctx, parts[1])
        except commands.BadArgument:
            await ctx.send("Role not found.")
            return
        await ctx.invoke(bot.get_command("roleinfo"), role=role)
    else:
        await ctx.send("Usage: `role info <role>`")


# ------------------------ Server Invite Slash Command ------------------------

# Slash command /discord invite
@discord_group.command(name="invite", description="Get the server's invite link")
async def discord_invite_slash(interaction: discord.Interaction):
    guild = interaction.guild

    invites = await guild.invites()
    invite = invites[0] if invites else await interaction.channel.create_invite(max_age=0, reason="Requested by user")

    if invite:
        embed = discord.Embed(
            title="🔗 Server Invite Link",
            description=f"This is the invite to join the server:\n{invite.url}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title=f"{failed_emoji} Server Invite Error",
            description="Unable to create or fetch an invite. Please check my permissions.",
            color=discord.Color.red()
        )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)




# --------- Prefix command for !discord invite ---------

@bot.command(name="discord")
async def discord_prefix(ctx, *, arg=None):
    if arg and arg.lower() == "invite":
        await ctx.invoke(bot.get_command("invite"))
    else:
        await ctx.send("Usage: `!discord invite`")

# --------- Prefix command !invite ---------

@bot.command(name="invite")
async def invite_prefix(ctx):
    guild = ctx.guild
    invites = await guild.invites()
    invite = invites[0] if invites else await ctx.channel.create_invite(max_age=0, reason="Requested by user")

    if invite:
        embed = discord.Embed(
            title="🔗 Server Invite Link",
            description=f"This is the invite to join the server:\n{invite.url}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="{failed_emoji} Server Invite Error",
            description="Unable to create or fetch an invite. Please check my permissions.",
            color=discord.Color.red()
        )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# --------- Prefix command !discordinvite ---------

@bot.command(name="discordinvite")
async def discordinvite_prefix(ctx):
    await ctx.invoke(bot.get_command("invite"))

# ------------------------ Nickname Slash Command ------------------------

@tree.command(name="nickname", description="Change a user's nickname (Staff only)")
@app_commands.describe(user="The user to rename", new_nickname="The new nickname to assign")
async def nickname_slash(interaction: discord.Interaction, user: discord.Member, new_nickname: str):
    staff_role = interaction.guild.get_role(staff_role_id)

    if staff_role not in interaction.user.roles:
        embed = discord.Embed(
            description=f"{failed_emoji} You don't have permission to use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        await user.edit(nick=new_nickname, reason=f"Changed by {interaction.user}")
        embed = discord.Embed(
            description=f"{tick_emoji} {user.mention}'s nickname has been changed to **{new_nickname}**.",
            color=discord.Color.green()
        )
    except discord.Forbidden:
        embed = discord.Embed(
            description=f"{failed_emoji} I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ Nickname Prefix Command ------------------------

@bot.command(name="nickname")
async def nickname_prefix(ctx, user: discord.Member, *, new_nickname: str):
    staff_role = ctx.guild.get_role(staff_role_id)

    if staff_role not in ctx.author.roles:
        await ctx.message.add_reaction(failed_emoji)
        return

    try:
        await user.edit(nick=new_nickname, reason=f"Changed by {ctx.author}")
        embed = discord.Embed(
            description=f"{tick_emoji} {user.mention}'s nickname has been changed to **{new_nickname}**.",
            color=discord.Color.green()
        )
    except discord.Forbidden:
        embed = discord.Embed(
            description=f"{failed_emoji} I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ Reminder Slash Command Part 1 ------------------------

def parse_duration(time_str: str) -> int:
    """Parses a time string like '1d2h30m15s' into total seconds."""
    time_units = {
        'd': 86400,  # days
        'h': 3600,   # hours
        'm': 60,     # minutes
        's': 1       # seconds
    }

    matches = re.findall(r'(\d+)([dhms])', time_str.lower())
    if not matches:
        raise ValueError("Invalid time format. Use something like `1d2h30m15s`.")

    total_seconds = 0
    for amount, unit in matches:
        if unit in time_units:
            total_seconds += int(amount) * time_units[unit]
        else:
            raise ValueError(f"Unknown time unit: {unit}")

    return total_seconds

# ------------------------ Reminder Slash Command Part 2 ------------------------

@tree.command(name="reminder", description="Set a personal reminder")
@app_commands.describe(time="Time format like 1d2h30m15s", reminder="Reminder message")
async def reminder_slash(interaction: discord.Interaction, time: str, reminder: str):
    try:
        seconds = parse_duration(time)
    except ValueError as e:
        embed = discord.Embed(
            description=f"{failed_emoji} {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        description=f"{time_emoji} Reminder set for `{time}`.\n> {reminder}",
        color=discord.Color.blue()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    await asyncio.sleep(seconds)

    try:
        reminder_embed = discord.Embed(
            title=f"{time_emoji} Reminder",
            description=reminder,
            color=discord.Color.green()
        )
        reminder_embed.set_footer(text="SWAT Roleplay Community")
        await interaction.user.send(embed=reminder_embed)
    except discord.Forbidden:
        await interaction.followup.send(f"{failed_emoji} I couldn't DM you your reminder.", ephemeral=True)

# ------------------------ Reminder Prefix Command ------------------------

@bot.command(name="reminder")
async def reminder_prefix(ctx, time: str, *, reminder: str):
    try:
        seconds = parse_duration(time)
    except ValueError as e:
        await ctx.send(f"{failed_emoji} {str(e)}", delete_after=10)
        return

    embed = discord.Embed(
        description=f"{time_emoji} Reminder set for `{time}`.\n> {reminder}",
        color=discord.Color.blue()
    )
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

    await asyncio.sleep(seconds)

    try:
        reminder_embed = discord.Embed(
            title=f"{time_emoji} Reminder",
            description=reminder,
            color=discord.Color.green()
        )
        reminder_embed.set_footer(text="SWAT Roleplay Community")
        await ctx.author.send(embed=reminder_embed)
    except discord.Forbidden:
        await ctx.send(f"{failed_emoji} I couldn't DM you your reminder.")

# ------------------------ Alias: .remindme ------------------------

@bot.command(name="remindme")
async def remindme_alias(ctx, time: str, *, reminder: str):
    await ctx.invoke(bot.get_command("reminder"), time=time, reminder=reminder)

# ------------------------ Error logs Slash Command Part 1 ------------------------

async def send_long_message(destination, content):
    max_len = 1990  # Leave room for ``` formatting
    if len(content) <= max_len:
        await destination.send(f"```\n{content}\n```")
    else:
        parts = [content[i:i + max_len] for i in range(0, len(content), max_len)]
        for part in parts:
            await destination.send(f"```\n{part}\n```")

# ------------------------ Error logs Slash Command Part 2 ------------------------

@error_group.command(name="logs", description="View the error log file")
async def error_logs_slash(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not os.path.exists("error_logs.txt"):
        embed = discord.Embed(
            description="{failed_emoji} No error logs found.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    with open("error_logs.txt", "r") as file:
        content = file.read()

    await send_long_message(interaction.followup, content)

# ------------------------ Error Logs Prefix Command ------------------------

@bot.command(name="errorlogs", aliases=["errors", "error"])
async def errorlogs_prefix(ctx, *args):
    if args and args[0].lower() == "logs":
        # Handles !error logs
        pass  # continue below
    elif ctx.invoked_with not in ["errorlogs", "errors", "error"]:
        return  # Not a recognized command

    if not os.path.exists("error_logs.txt"):
        embed = discord.Embed(
            description="{failed_emoji} No error logs found.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    with open("error_logs.txt", "r") as file:
        content = file.read()

    await send_long_message(ctx, content)

# ------------------------ Suggestion Slash Command ------------------------

@bot.tree.command(name="suggestion", description="Submit a suggestion for the bot or server.")
@app_commands.describe(suggestion="Your suggestion (10+ characters)")
async def suggestion_slash(interaction: discord.Interaction, suggestion: str):
    def styled_embed(title: str, description: str, color: discord.Color):
        embed = discord.Embed(title=title, description=description, color=color)
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        return embed

    if not suggestion or len(suggestion.strip()) < 10:
        error_embed = styled_embed(
            f"{failed_emoji} Invalid Suggestion",
            "Please provide a valid suggestion (at least 10 characters).",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    suggestion_channel_id = 1343622169086918758
    suggestion_channel = interaction.guild.get_channel(suggestion_channel_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    suggestion_embed = discord.Embed(
        title="💡 New Suggestion",
        description=suggestion,
        color=discord.Color.blue()
    )
    suggestion_embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
    suggestion_embed.add_field(name="User ID", value=interaction.user.id, inline=True)
    suggestion_embed.add_field(name="Submitted At", value=timestamp, inline=True)

    if interaction.guild and interaction.guild.icon:
        suggestion_embed.set_thumbnail(url=interaction.guild.icon.url)

    suggestion_embed.set_footer(text="SWAT Roleplay Community")

    await suggestion_channel.send(embed=suggestion_embed)

    confirm_embed = styled_embed(
        f"{tick_emoji} Suggestion Submitted",
        "Thank you for your suggestion! It has been submitted.",
        discord.Color.blue()
    )
    await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

# ------------------------ Suggestion Prefix Command ------------------------

@bot.command(name="suggestion", aliases=["suggest"])
async def suggestion_prefix(ctx, *, suggestion: str = None):
    if not suggestion or len(suggestion) < 10:
        await ctx.send(f"{failed_emoji} Please provide a valid suggestion (at least 10 characters).", delete_after=10)
        return

    suggestion_channel_id = 1343622169086918758
    suggestion_channel = ctx.guild.get_channel(suggestion_channel_id)

    embed = discord.Embed(
        title="💡 New Suggestion",
        description=suggestion,
        color=discord.Color.green()
    )
    embed.add_field(name="Submitted by", value=ctx.author.mention, inline=True)
    embed.add_field(name="User ID", value=ctx.author.id, inline=True)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    await suggestion_channel.send(embed=embed)
    await ctx.message.add_reaction(tick_emoji)

# ------------------------ Staff Suggestion Slash Command ------------------------

@bot.tree.command(name="staff_suggestion", description="Submit a staff suggestion for the bot or server.")
@app_commands.describe(staff_suggestion="Your suggestion (10+ characters)")
@app_commands.checks.has_role(int(staff_role_id))  # Ensure staff_role_id is int or cast it
async def staff_suggestion_slash(interaction: discord.Interaction, staff_suggestion: str):
    def styled_embed(title: str, description: str, color: discord.Color):
        embed = discord.Embed(title=title, description=description, color=color)
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        return embed

    if len(staff_suggestion.strip()) < 10:
        error_embed = styled_embed(
            f"{failed_emoji} Invalid Suggestion",
            "Please provide a valid suggestion (at least 10 characters).",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    staff_suggestion_channel_id = 1373704702977376297
    suggestion_channel = interaction.guild.get_channel(staff_suggestion_channel_id)

    if not suggestion_channel:
        error_embed = styled_embed(
            f"{failed_emoji} Channel Not Found",
            "Suggestion channel not found. Please contact an admin.",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    embed = discord.Embed(
        title="🛠️ New Staff Suggestion",
        description=staff_suggestion,
        color=discord.Color.blue()
    )
    embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
    embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
    embed.add_field(name="Submitted At", value=timestamp, inline=True)

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    await suggestion_channel.send(embed=embed)

    confirm_embed = styled_embed(
        f"{tick_emoji} Suggestion Submitted",
        "Thank you for your staff suggestion! It has been sent to the team.",
        discord.Color.blue()
    )
    await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

# ------------------------ Slash Command error handler ------------------------

@staff_suggestion_slash.error
async def staff_suggestion_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRole):
        embed = discord.Embed(
            title=f"{failed_emoji} Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------------ Staff Suggestion Prefix Command ------------------------

@bot.command(name="staffsuggestion", aliases=["staff", "staff_suggestion"])
async def staff_suggestion_prefix(ctx, *, suggestion: str = None):
    staff_role_id = 1343234687505530902  # Replace with your staff role ID

    if not any(role.id == staff_role_id for role in ctx.author.roles):
        await ctx.message.add_reaction(failed_emoji)
        return

    if not suggestion or len(suggestion.strip()) < 10:
        await ctx.send(f"{failed_emoji} Please provide a valid suggestion (at least 10 characters).", delete_after=10)
        return

    suggestion_channel_id = 1373704702977376297
    suggestion_channel = ctx.guild.get_channel(suggestion_channel_id)

    if not suggestion_channel:
        await ctx.send(f"{failed_emoji} Suggestion channel not found.")
        return

    embed = discord.Embed(
        title="🛠️ New Staff Suggestion",
        description=suggestion,
        color=discord.Color.green()
    )
    embed.add_field(name="Submitted by", value=ctx.author.mention, inline=True)
    embed.add_field(name="User ID", value=str(ctx.author.id), inline=True)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    await suggestion_channel.send(embed=embed)
    await ctx.message.add_reaction(tick_emoji)


# ------------------------ Staff Feedback Slash Command ------------------------

@bot.tree.command(name="staff_feedback", description="Submit feedback for a staff member.")
@app_commands.describe(text="Your feedback (10+ characters)", staff="The staff member")
async def staff_feedback_slash(interaction: discord.Interaction, text: str, staff: discord.Member):

    def styled_embed(title: str, description: str, color: discord.Color):
        embed = discord.Embed(title=title, description=description, color=color)
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        return embed

    if interaction.user == staff:
        embed = styled_embed(
            f"{failed_emoji} Feedback Rejected",
            "You cannot give feedback to yourself.",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if staff_role_id not in [role.id for role in staff.roles]:
        embed = styled_embed(
            f"{failed_emoji} Feedback Rejected",
            f"{staff.mention} does not have the required staff role.",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not text or len(text.strip()) < 10:
        embed = styled_embed(
            f"{failed_emoji} Invalid Feedback",
            "Please provide valid feedback (at least 10 characters).",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    staff_feedback_channel_id = 1343621982549311519
    feedback_channel = interaction.guild.get_channel(staff_feedback_channel_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    feedback_embed = discord.Embed(
        title=f"{clipboard_emoji} Staff Feedback",
        description=text,
        color=discord.Color.blue()
    )
    feedback_embed.add_field(name="Feedback for", value=staff.mention, inline=True)
    feedback_embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
    feedback_embed.add_field(name="Submitted At", value=timestamp, inline=True)

    if interaction.guild and interaction.guild.icon:
        feedback_embed.set_thumbnail(url=interaction.guild.icon.url)

    feedback_embed.set_footer(text="SWAT Roleplay Community")

    await feedback_channel.send(f"-# {ping_emoji} {staff.mention}", embed=feedback_embed)

    confirm_embed = styled_embed(
        f"{tick_emoji} Feedback Submitted",
        f"Thank you for your feedback about {staff.mention}.",
        discord.Color.green()
    )
    await interaction.response.send_message(embed=confirm_embed, ephemeral=True)


# ------------------------ Staff Feedback Prefix Command ------------------------

@bot.command(name="stafffeedback", aliases=["staff_feedback"])
async def staff_feedback_prefix(ctx, staff: discord.Member = None, *, text: str = None):

    if not staff or not text:
        await ctx.send(f"{failed_emoji} Usage: `!stafffeedback @User <feedback>`", delete_after=10)
        return

    if ctx.author == staff:
        await ctx.send(f"{failed_emoji} You cannot give feedback to yourself.", delete_after=10)
        return

    if staff_role_id not in [role.id for role in staff.roles]:
        await ctx.send(f"{failed_emoji} {staff.mention} does not have the required staff role.", delete_after=10)
        return

    if len(text.strip()) < 10:
        await ctx.send(f"{failed_emoji} Feedback must be at least 10 characters.", delete_after=10)
        return

    staff_feedback_channel_id = 1343621982549311519
    feedback_channel = ctx.guild.get_channel(staff_feedback_channel_id)

    embed = discord.Embed(
        title=f"{clipboard_emoji} Staff Feedback",
        description=text,
        color=discord.Color.blue()
    )
    embed.add_field(name="Feedback for", value=staff.mention, inline=True)
    embed.add_field(name="Submitted by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Time", value=ctx.author.id, inline=True)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    await feedback_channel.send(f"-# {ping_emoji} {staff.mention}", embed=embed)
    await ctx.message.add_reaction(tick_emoji)
    
# ------------------------ Events ------------------------

# Load events from the JSON file
def load_events():
    global events
    try:
        with open("events.json", "r") as file:
            events = json.load(file)
    except FileNotFoundError:
        events = []

# Save events to the JSON file
def save_events():
    with open("events.json", "w") as file:
        json.dump(events, file, indent=4)

# ------------------------ Create Event Slash Command ------------------------

@bot.tree.command(name="event", description="Create an event")
@app_commands.describe(
    event_name="Name of the event",
    event_date="Date in YYYY-MM-DD format",
    event_time="Time in HH:MM 24-hour format",
    event_description="Description of the event"
)
async def event_slash(interaction: discord.Interaction, event_name: str, event_date: str, event_time: str, event_description: str):
    # Role check
    if event_role_id not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message(f"{failed_emoji} You do not have permission to create events.", ephemeral=True)
        return

    # Parse datetime
    try:
        event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        await interaction.response.send_message(
            "Invalid date/time format. Please use 'YYYY-MM-DD' for the date and 'HH:MM' (24-hour) for the time.",
            ephemeral=True
        )
        return

    # Save event
    event_data = {
        "name": event_name,
        "date": event_datetime.strftime("%Y-%m-%d"),
        "time": event_datetime.strftime("%H:%M"),
        "description": event_description,
        "creator": interaction.user.name
    }
    events.append(event_data)
    save_events()

    embed = discord.Embed(
        title=f"Event Created: {event_name}",
        description=(
            f"**Date:** {event_datetime.strftime('%Y-%m-%d')}\n"
            f"**Time:** {event_datetime.strftime('%H:%M')}\n"
            f"**Description:** {event_description}\n"
            f"**Creator:** {interaction.user.name}"
        ),
        color=discord.Color.green()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ Create Event Prefix Command ------------------------

@bot.command(name="event")
async def event_prefix(ctx, event_name: str, event_date: str, event_time: str, *, event_description: str):
    # Role check
    if event_role_id not in [role.id for role in ctx.author.roles]:
        await ctx.send(f"{failed_emoji} You do not have permission to create events.", delete_after=10)
        return

    try:
        event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        await ctx.send("Invalid date/time format. Please use 'YYYY-MM-DD' for the date and 'HH:MM' (24-hour) for the time.", delete_after=10)
        return

    event_data = {
        "name": event_name,
        "date": event_datetime.strftime("%Y-%m-%d"),
        "time": event_datetime.strftime("%H:%M"),
        "description": event_description,
        "creator": ctx.author.name
    }
    events.append(event_data)
    save_events()

    embed = discord.Embed(
        title=f"Event Created: {event_name}",
        description=(
            f"**Date:** {event_datetime.strftime('%Y-%m-%d')}\n"
            f"**Time:** {event_datetime.strftime('%H:%M')}\n"
            f"**Description:** {event_description}\n"
            f"**Creator:** {ctx.author.name}"
        ),
        color=discord.Color.green()
    )
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ View Events Slash Command ------------------------

@bot.tree.command(name="events", description="View upcoming events")
async def events_slash(interaction: discord.Interaction):
    if not events:
        await interaction.response.send_message("There are no upcoming events at the moment.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Upcoming Events",
        description="Here are the upcoming events for the server:",
        color=discord.Color.blue()
    )

    for event in events:
        embed.add_field(
            name=event["name"],
            value=(
                f"**Date:** {event['date']}\n"
                f"**Time:** {event['time']}\n"
                f"**Description:** {event['description']}\n"
                f"**Creator:** {event['creator']}"
            ),
            inline=False
        )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)

# ------------------------ View Events Prefix Command ------------------------

@bot.command(name="events", aliases=["eventlist"])
async def events_prefix(ctx):
    if not events:
        await ctx.send("There are no upcoming events at the moment.", delete_after=10)
        return

    embed = discord.Embed(
        title="Upcoming Events",
        description="Here are the upcoming events for the server:",
        color=discord.Color.blue()
    )

    for event in events:
        embed.add_field(
            name=event["name"],
            value=(
                f"**Date:** {event['date']}\n"
                f"**Time:** {event['time']}\n"
                f"**Description:** {event['description']}\n"
                f"**Creator:** {event['creator']}"
            ),
            inline=False
        )

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)

# ------------------------ Shutdown Slash Command ------------------------

@bot.tree.command(name="shutdown", description="Shut down the bot (owner only)")
async def shutdown_slash(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        embed = discord.Embed(
            description=f"{failed_emoji} You do not have permission to shut down the bot.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        description=f"{failed_emoji} Shutting down the bot... Goodbye!",
        color=discord.Color.red()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed, ephemeral=True)
    await bot.close()


# ------------------------ Shutdown Prefix Command ------------------------

@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown_prefix(ctx):
    embed_no_perm = discord.Embed(
        description=f"{failed_emoji} You do not have permission to shut down the bot.",
        color=discord.Color.red()
    )
    if ctx.guild and ctx.guild.icon:
        embed_no_perm.set_thumbnail(url=ctx.guild.icon.url)
    embed_no_perm.set_footer(text="SWAT Roleplay Community")

    # Check if author is owner
    if ctx.author.id != OWNER_ID:
        await ctx.send(embed=embed_no_perm, delete_after=10)
        return

    embed = discord.Embed(
        description=f"{failed_emoji} Shutting down the bot... Goodbye!",
        color=discord.Color.red()
    )
    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await ctx.send(embed=embed)
    await bot.close()

# ------------------------ Report Slash Command ------------------------

REPORT_CHANNEL_ID = 1343300143830798336

@bot.tree.command(name="report", description="Report a user to the moderators")
@app_commands.describe(user="The user you want to report", reason="The reason for the report")
async def report_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    # Timestamp for reporting
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Create the report embed
    embed = discord.Embed(
        title="🚨 New User Report",
        color=discord.Color.red()
    )
    embed.add_field(name="Reporter", value=interaction.user.mention, inline=True)
    embed.add_field(name="Reported User", value=user.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Channel", value=f"#{interaction.channel.name}", inline=True)
    embed.add_field(name="Time", value=timestamp, inline=True)

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    mod_channel = interaction.guild.get_channel(REPORT_CHANNEL_ID)

    if mod_channel:
        # Ping staff help role and send embed
        await mod_channel.send(f"<@&{staff_help_role_id}> New report received:", embed=embed)

        # Confirm to user
        confirm_embed = discord.Embed(
            title=f"{tick_emoji} Report Submitted",
            description="Your report has been sent to the staff team. Thank you for helping keep the server safe.",
            color=discord.Color.blue()
        )
        if interaction.guild and interaction.guild.icon:
            confirm_embed.set_thumbnail(url=interaction.guild.icon.url)
        confirm_embed.set_footer(text="SWAT Roleplay Community")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
    else:
        error_embed = discord.Embed(
            title=f"{failed_emoji} Report Failed",
            description="The report channel could not be found. Please contact staff manually.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            error_embed.set_thumbnail(url=interaction.guild.icon.url)
        error_embed.set_footer(text="SWAT Roleplay Community")

        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# ------------------------ Report Prefix Command ------------------------

@bot.command(name="report")
async def report_prefix(ctx, user: discord.Member, *, reason: str):
    embed = discord.Embed(
        title="🚨 New User Report",
        description=(
            f"**Reporter:** {ctx.author.mention}\n"
            f"**Reported User:** {user.mention}\n"
            f"**Reason:** {reason}"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text=f"User ID: {user.id} | Reported from: #{ctx.channel.name}")
    embed.timestamp = discord.utils.utcnow()

    mod_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if mod_channel:
        await mod_channel.send(embed=embed)
        confirm_embed = discord.Embed(
            title="Report Submitted",
            description="Your report has been sent to the moderators. Thank you.",
            color=discord.Color.green()
        )
        if ctx.guild and ctx.guild.icon:
            confirm_embed.set_thumbnail(url=ctx.guild.icon.url)
        confirm_embed.set_footer(text="SWAT Roleplay Community")

        await ctx.send(embed=confirm_embed, delete_after=15)
    else:
        error_embed = discord.Embed(
            title="Error",
            description="Could not find the report channel. Please contact staff.",
            color=discord.Color.red()
        )
        if ctx.guild and ctx.guild.icon:
            error_embed.set_thumbnail(url=ctx.guild.icon.url)
        error_embed.set_footer(text="SWAT Roleplay Community")

        await ctx.send(embed=error_embed, delete_after=15)

# ------------------------ DM Stuff ------------------------

def parse_color(color_str: str) -> discord.Color:
    c = color_str.strip()
    if c.startswith("#"):
        try:
            return discord.Color(int(c[1:], 16))
        except ValueError:
            return discord.Color.default()
    else:
        simple_colors = {
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "blue": discord.Color.blue(),
            "blurple": discord.Color.blurple(),
            "grey": discord.Color.greyple(),
            "purple": discord.Color.purple(),
            "gold": discord.Color.gold(),
            "orange": discord.Color.orange(),
            "teal": discord.Color.teal(),
            "default": discord.Color.default(),
        }
        return simple_colors.get(c.lower(), discord.Color.default())

# --- Modals for embed parts ---

class EditTitleModal(discord.ui.Modal):
    title_input = discord.ui.TextInput(label="New Title", max_length=256, required=True)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Title"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        embed.title = self.title_input.value
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Embed title updated!", ephemeral=True)

class EditDescriptionModal(discord.ui.Modal):
    description_input = discord.ui.TextInput(label="New Description", style=discord.TextStyle.paragraph, max_length=4000, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Description"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        embed.description = self.description_input.value
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Embed description updated!", ephemeral=True)

class EditColorModal(discord.ui.Modal):
    color_input = discord.ui.TextInput(label="Color (Hex or name)", max_length=20, required=False, placeholder="#7289DA or red")

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Color"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        color_str = self.color_input.value
        embed.color = parse_color(color_str) if color_str else discord.Color.default()
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Embed color updated!", ephemeral=True)

class EditImageModal(discord.ui.Modal):
    image_url_input = discord.ui.TextInput(label="Image URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Image URL"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        url = self.image_url_input.value.strip()
        if url:
            embed.set_image(url=url)
        else:
            embed.set_image(url=None)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Embed image updated!", ephemeral=True)

class EditFooterTextModal(discord.ui.Modal):
    footer_text_input = discord.ui.TextInput(label="Footer Text", max_length=2048, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Footer Text"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        footer_icon_url = embed.footer.icon_url if embed.footer else None
        embed.set_footer(text=self.footer_text_input.value, icon_url=footer_icon_url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Footer text updated!", ephemeral=True)

class EditFooterIconModal(discord.ui.Modal):
    footer_icon_input = discord.ui.TextInput(label="Footer Icon URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Footer Icon URL"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        footer_text = embed.footer.text if embed.footer else None
        url = self.footer_icon_input.value.strip()
        if url == "":
            url = None
        embed.set_footer(text=footer_text, icon_url=url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Footer icon updated!", ephemeral=True)

class EditAuthorNameModal(discord.ui.Modal):
    author_name_input = discord.ui.TextInput(label="Author Name", max_length=256, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Author Name"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        icon_url = embed.author.icon_url if embed.author else None
        embed.set_author(name=self.author_name_input.value or discord.Embed.Empty, icon_url=icon_url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Author name updated!", ephemeral=True)

class EditAuthorIconModal(discord.ui.Modal):
    author_icon_input = discord.ui.TextInput(label="Author Icon URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Author Icon URL"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        name = embed.author.name if embed.author else None
        url = self.author_icon_input.value.strip()
        if url == "":
            url = None
        embed.set_author(name=name or discord.Embed.Empty, icon_url=url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Author icon updated!", ephemeral=True)

class EditThumbnailModal(discord.ui.Modal):
    thumbnail_url_input = discord.ui.TextInput(label="Thumbnail URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Embed Thumbnail URL"

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        url = self.thumbnail_url_input.value.strip()
        if url:
            embed.set_thumbnail(url=url)
        else:
            embed.set_thumbnail(url=None)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("{tick_emoji} Thumbnail updated!", ephemeral=True)

# --- New modal for message content ---

class EditMessageContentModal(discord.ui.Modal):
    message_content_input = discord.ui.TextInput(label="Message Content", style=discord.TextStyle.paragraph, max_length=2000, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Edit Message Content"

    async def on_submit(self, interaction: discord.Interaction):
        new_content = self.message_content_input.value
        await self.embed_message.edit(content=new_content, embed=self.embed_message.embeds[0] if self.embed_message.embeds else None)
        await interaction.response.send_message("{tick_emoji} Message content updated!", ephemeral=True)

# --- Modal for Send to User (sends message content + embed) ---

class SendToUserModal(discord.ui.Modal):
    user_id_input = discord.ui.TextInput(label="User ID", max_length=30, required=True, placeholder="Enter the user ID to DM")

    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message
        self.title = "Send to User"

    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id_input.value.strip()
        try:
            user = await bot.fetch_user(int(user_id))
            if user is None:
                await interaction.response.send_message("{failed_emoji} Could not find user with that ID.", ephemeral=True)
                return
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("{failed_emoji} Invalid user ID.", ephemeral=True)
            return

        content = self.embed_message.content or ""
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else None

        try:
            await user.send(content=content, embed=embed)
            await interaction.response.send_message(f"{tick_emoji} Sent message and embed to {user}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("{failed_emoji} I can't DM that user. They might have DMs disabled.", ephemeral=True)

# --- The buttons view ---

class EmbedEditView(discord.ui.View):
    def __init__(self, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.embed_message = embed_message

    @discord.ui.button(label="Edit Message Content", style=discord.ButtonStyle.primary, custom_id="edit_message_content")
    async def edit_message_content(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditMessageContentModal(self.embed_message))

    @discord.ui.button(label="Edit Title", style=discord.ButtonStyle.primary, custom_id="edit_title")
    async def edit_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTitleModal(self.embed_message))

    @discord.ui.button(label="Edit Description", style=discord.ButtonStyle.secondary, custom_id="edit_description")
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditDescriptionModal(self.embed_message))

    @discord.ui.button(label="Edit Color", style=discord.ButtonStyle.success, custom_id="edit_color")
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditColorModal(self.embed_message))

    @discord.ui.button(label="Edit Image URL", style=discord.ButtonStyle.secondary, custom_id="edit_image")
    async def edit_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditImageModal(self.embed_message))

    @discord.ui.button(label="Edit Footer Text", style=discord.ButtonStyle.secondary, custom_id="edit_footer_text")
    async def edit_footer_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditFooterTextModal(self.embed_message))

    @discord.ui.button(label="Edit Footer Icon", style=discord.ButtonStyle.secondary, custom_id="edit_footer_icon")
    async def edit_footer_icon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditFooterIconModal(self.embed_message))

    @discord.ui.button(label="Edit Author Name", style=discord.ButtonStyle.secondary, custom_id="edit_author_name")
    async def edit_author_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditAuthorNameModal(self.embed_message))

    @discord.ui.button(label="Edit Author Icon", style=discord.ButtonStyle.secondary, custom_id="edit_author_icon")
    async def edit_author_icon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditAuthorIconModal(self.embed_message))

    @discord.ui.button(label="Edit Thumbnail URL", style=discord.ButtonStyle.secondary, custom_id="edit_thumbnail")
    async def edit_thumbnail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditThumbnailModal(self.embed_message))

    @discord.ui.button(label="Send to User", style=discord.ButtonStyle.danger, custom_id="send_to_user")
    async def send_to_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SendToUserModal(self.embed_message))

# ------------------------ DM Slash Command ------------------------

@bot.tree.command(name="dm", description="Send yourself a DM with an editable embed and message content")
async def dm(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Editable Embed Title",
        description="This is your editable embed description.\nUse the buttons below to edit parts of it.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Edit me using the buttons!")

    # Add guild icon thumbnail if available
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    try:
        dm_channel = await interaction.user.create_dm()
        sent_message = await dm_channel.send(content="Your message content here (edit me)", embed=embed)
        view = EmbedEditView(embed_message=sent_message)
        await sent_message.edit(view=view)
        await interaction.response.send_message("📬 I sent you a DM with the editable embed and message!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("{failed_emoji} I couldn't DM you. Please check your privacy settings.", ephemeral=True)

# ------------------------ DM Prefix Command ------------------------

@bot.command(name="dm")
async def dm_prefix(ctx):
    embed = discord.Embed(
        title="Editable Embed Title",
        description="This is your editable embed description.\nUse the buttons below to edit parts of it.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Edit me using the buttons!")

    try:
        dm_channel = await ctx.author.create_dm()
        sent_message = await dm_channel.send(content="Your message content here (edit me)", embed=embed)
        view = EmbedEditView(embed_message=sent_message)
        await sent_message.edit(view=view)
        await ctx.send("📬 I sent you a DM with the editable embed and message!", delete_after=15)
    except discord.Forbidden:
        await ctx.send("{failed_emoji} I couldn't DM you. Please check your privacy settings.", delete_after=15)










































# ------------------------ ER:LC Configuration ------------------------

API_KEY = os.getenv("API_KEY")
API_BASE = "https://api.policeroleplay.community/v1/server"
PRIV_ROLE_ID = 1316076187893891083
ROBLOX_USER_API = "https://users.roblox.com/v1/users"
LOGS_CHANNEL_ID = 1381267054354632745
ENDPOINTS = ["modcalls", "killlogs", "joinlogs"]
WELCOME_TEMPLATE = "Welcome to the server!"
KICK_REASON = "Username not allowed (starts with All or Others)"
PLAYERCOUNT_VC_ID = 1381697147895939233  
QUEUE_VC_ID = 1381697165562347671         
PLAYERCOUNT_PREFIX = "「🎮」In Game:"
QUEUE_PREFIX = "「⏳」In Queue:"
DISCORD_CHANNEL_ID = 1381267054354632745   

 
RESTRICTED_VEHICLES = {
    "Bugatti Veyron": [123456789012345678],  
    "Tesla Roadster": [234567890123456789],   
}

# Roblox-Discord links
ROBLOX_DISCORD_LINKS = {
    "PlayerName123": 345678901234567890,   
    "VIPUser987": 123456789012345678,      
}

# Voice channel abbreviation map
VC_ABBREVIATIONS = {
    "MS1": 112233445566778800,
    "MS2": 112233445566778801,
    "STAFF": 112233445566778802,
    "G1": 112233445566778803,
    "G2": 112233445566778804,
    "M": 112233445566778805
}

# Roblox username to Discord user ID
ROBLOX_TO_DISCORD = {
    "ModUser1": 998877665544332211,
    "ModUser2": 887766554433221100
}

welcomed_players = set()
handled_usernames = set()
last_checked_time = 0

HEADERS_GET = {
    "server-key": API_KEY,
    "Accept": "*/*"
}
HEADERS_POST = {
    "server-key": API_KEY,
    "Content-Type": "application/json"
}

 
COMMAND_LOG_CHANNEL_ID = 1381267054354632745
JOIN_LEAVE_LOG_CHANNEL_ID = 1381267054354632745
KILL_LOG_CHANNEL_ID = 1381267054354632745
ALERT_LOG_CHANNEL_ID = 1381267054354632745

async def send_embed(channel_id: int, embed: discord.Embed):
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.warning(f"Channel with ID {channel_id} not found")
        return
    await channel.send(embed=embed)

# === HANDLE ERROR CODES ===
def get_error_message(http_status: int, api_code: str = None) -> str:
    messages = {
        0: f"{error_emoji} **0 – Unknown Error**: An unknown error occurred. Please contact support if this continues.",
        100: f"{error_emoji} **100 – Continue**: The request headers were received, continue with the request body.",
        101: f"{error_emoji} **101 – Switching Protocols**: The server is switching protocols.",
        200: f"{error_emoji} **200 – OK**: The request completed successfully.",
        201: f"{error_emoji} **201 – Created**: The request succeeded and a new resource was created.",
        204: f"{error_emoji} **204 – No Content**: Success, but no content returned.",
        400: f"{error_emoji} **400 – Bad Request**: The request was malformed or invalid.",
        401: f"{error_emoji} **401 – Unauthorized**: Missing or invalid authentication.",
        403: f"{error_emoji} **403 – Forbidden**: You do not have permission to access this resource.",
        404: f"{error_emoji} **404 – Not Found**: The requested resource does not exist.",
        405: f"{error_emoji} **405 – Method Not Allowed**: That method is not allowed on this endpoint.",
        408: f"{error_emoji} **408 – Request Timeout**: The server timed out waiting for the request.",
        409: f"{error_emoji} **409 – Conflict**: The request could not be completed due to a conflict.",
        410: f"{error_emoji} **410 – Gone**: The resource has been permanently removed.",
        415: f"{error_emoji} **415 – Unsupported Media Type**: The media type is not supported.",
        418: f"{error_emoji} **418 – I'm a teapot**: The server refuses to brew coffee in a teapot.",
        422: f"{error_emoji} **422 – No Players**: No players are currently in the private server.",
        429: f"{error_emoji} **429 – Too Many Requests**: You are being rate-limited. Slow down.",
        500: f"{error_emoji} **500 – Internal Server Error**: An internal server error occurred (possibly with Roblox).",
        501: f"{error_emoji} **501 – Not Implemented**: The server doesn't recognize this method.",
        502: f"{error_emoji} **502 – Bad Gateway**: Invalid response from an upstream server.",
        503: f"{error_emoji} **503 – Service Unavailable**: The server is overloaded or under maintenance.",
        504: f"{error_emoji} **504 – Gateway Timeout**: The upstream server did not respond in time.",
        1001: f"{error_emoji} **1001 – Communication Error**: Failed to communicate with Roblox or the in-game server.",
        1002: f"{error_emoji} **1002 – System Error**: A backend error occurred. Try again later.",
        2000: f"{error_emoji} **2000 – Missing Server Key**: No server-key provided.",
        2001: f"{error_emoji} **2001 – Bad Server Key Format**: Server-key format is invalid.",
        2002: f"{error_emoji} **2002 – Invalid Server Key**: The server-key is incorrect or expired.",
        2003: f"{error_emoji} **2003 – Invalid Global API Key**: The global API key is invalid.",
        2004: f"{error_emoji} **2004 – Banned Server Key**: Your server-key is banned from using the API.",
        3001: f"{error_emoji} **3001 – Missing Command**: No command was specified in the request body.",
        3002: f"{error_emoji} **3002 – Server Offline**: The server is currently offline or empty.",
        4001: f"{error_emoji} **4001 – Rate Limited**: You are being rate limited. Please wait and try again.",
        4002: f"{error_emoji} **4002 – Command Restricted**: The command you’re trying to run is restricted.",
        4003: f"{error_emoji} **4003 – Prohibited Message**: The message you’re trying to send is not allowed.",
        9998: f"{error_emoji} **9998 – Resource Restricted**: You are trying to access a restricted resource.",
        9999: f"{error_emoji} **9999 – Module Outdated**: The in-game module is outdated. Please restart the server.",
    }

    base_message = messages.get(http_status, f"{error_emoji} **{http_status} – Unknown Error**: An unexpected error occurred.")
    if api_code:
        base_message += f"\nAPI Code: `{api_code}`"
    return base_message

# === PRC COMMAND ===
def build_embed(title: str, description: str, color: discord.Color, guild: discord.Guild | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")
    return embed

async def send_command_to_api(command: str) -> tuple[bool, str | None]:
    payload = {"command": command}
    try:
        async with session.post(f"{API_BASE}/command", headers=HEADERS_POST, json=payload) as resp:
            if resp.status != 200:
                try:
                    data = await resp.json()
                    api_code = data.get("code")
                except Exception:
                    api_code = None
                return False, get_error_message(resp.status, api_code)
    except Exception as e:
        return False, f"{error_emoji} Exception occurred while sending command: `{e}`"
    return True, None

@erlc_group.command(name="command", description="Run a server command like :h, :m, :mod")
@discord.app_commands.describe(command="The command to run (e.g. ':h Hello', ':m message', ':mod')")
async def erlc_command(interaction: discord.Interaction, command: str):
    await interaction.response.defer()
    lowered = command.lower()

    # Block dangerous commands
    if any(word in lowered for word in ["ban", "unban", "kick"]):
        embed = build_embed(
            title=f"{error_emoji} Command Blocked",
            description="You are not allowed to use `ban`, `unban`, or `kick` commands.",
            color=discord.Color.red(),
            guild=interaction.guild
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Handle :log separately
    if lowered.startswith(":log "):
        message_to_log = command[5:].strip()
        if not message_to_log:
            embed = build_embed(
                title=f"{error_emoji} Missing Log Message",
                description="You must provide a message after `:log`.",
                color=discord.Color.red(),
                guild=interaction.guild
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        in_game_command = f":say [LOG] {message_to_log}"

        log_embed = discord.Embed(
            title="🛠 In-Game Log Message Sent",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        log_embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
        log_embed.add_field(name="Message", value=message_to_log, inline=False)
        if interaction.guild and interaction.guild.icon:
            log_embed.set_thumbnail(url=interaction.guild.icon.url)
        log_embed.set_footer(text="SWAT Roleplay Community")
        await send_embed(COMMAND_LOG_CHANNEL_ID, log_embed)

        success, error_msg = await send_command_to_api(in_game_command)
        if not success:
            await interaction.followup.send(error_msg, ephemeral=True)
            return

        await interaction.followup.send(
            f"{tick_emoji} Log message sent in-game: `{message_to_log}`", ephemeral=True)
        return

    # General command execution
    command_embed = discord.Embed(
        title="🛠 Command Executed",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    command_embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
    command_embed.add_field(name="Command", value=command, inline=False)
    if interaction.guild and interaction.guild.icon:
        command_embed.set_thumbnail(url=interaction.guild.icon.url)
    command_embed.set_footer(text="SWAT Roleplay Community")
    await send_embed(COMMAND_LOG_CHANNEL_ID, command_embed)

    success, error_msg = await send_command_to_api(command)
    if not success:
        await interaction.followup.send(error_msg, ephemeral=True)
        return

    await interaction.followup.send(f"{tick_emoji} Command `{command}` sent successfully.", ephemeral=True)




@tasks.loop(seconds=60)
async def join_leave_log_task():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/joinlogs", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch join logs: {resp.status}")
                return
            data = await resp.json()

    if not data:
        return

    channel = bot.get_channel(JOIN_LEAVE_LOG_CHANNEL_ID)
    if not channel:
        logger.warning("Join/leave log channel not found")
        return

    if not hasattr(join_leave_log_task, "last_ts"):
        join_leave_log_task.last_ts = 0

    new_entries = [entry for entry in data if entry.get("Timestamp", 0) > join_leave_log_task.last_ts]
    if not new_entries:
        return

    for entry in new_entries:
        ts = entry.get("Timestamp", 0)
        player = entry.get("Player", "Unknown")
        joined = entry.get("Join", True)
        status = "Joined" if joined else "Left"

        embed = discord.Embed(
            title="Player Join/Leave",
            color=discord.Color.green() if joined else discord.Color.red(),
            timestamp=datetime.fromtimestamp(ts, UTC)
        )
        embed.add_field(name="Player", value=player, inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.set_footer(text="SWAT Roleplay Community")

        await channel.send(embed=embed)

        if ts > join_leave_log_task.last_ts:
            join_leave_log_task.last_ts = ts


@tasks.loop(seconds=60)
async def kill_log_task():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/killlogs", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch kill logs: {resp.status}")
                return
            data = await resp.json()

    if not data:
        return

    channel = bot.get_channel(KILL_LOG_CHANNEL_ID)
    alert_channel = bot.get_channel(ALERT_LOG_CHANNEL_ID)
    if not channel:
        logger.warning("Kill log channel not found")
        return
    if not alert_channel:
        logger.warning("Alert log channel not found")

    if not hasattr(kill_log_task, "last_ts"):
        kill_log_task.last_ts = 0

    new_entries = [entry for entry in data if entry.get("Timestamp", 0) > kill_log_task.last_ts]
    if not new_entries:
        return

    for entry in new_entries:
        ts = entry.get("Timestamp", 0)
        killer = entry.get("Killer", "Unknown")
        killed = entry.get("Killed", "Unknown")

        embed = discord.Embed(
            title="🔪 Kill Log",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.fromtimestamp(ts, UTC)
        )
        embed.add_field(name="Killer", value=killer, inline=True)
        embed.add_field(name="Killed", value=killed, inline=True)
        embed.set_footer(text="SWAT Roleplay Community")

        await channel.send(embed=embed)

        killer_id = killer
        kill_tracker[killer_id].append(ts)
        while kill_tracker[killer_id] and (ts - kill_tracker[killer_id][0] > 60):
            kill_tracker[killer_id].popleft()

        if len(kill_tracker[killer_id]) >= 4:
            if alert_channel:
                alert_embed = discord.Embed(
                    title="🚨 Mass Kill Alert! 🚨",
                    description=f"**{killer}** has killed {len(kill_tracker[killer_id])} players within 1 minute.",
                    color=discord.Color.orange(),
                    timestamp=datetime.datetime.fromtimestamp(ts, UTC)
                )
                alert_embed.set_footer(text="PRC Alert System")
                await alert_channel.send(embed=alert_embed)

            kill_tracker[killer_id].clear()

        if ts > kill_log_task.last_ts:
            kill_log_task.last_ts = ts

@bot.tree.command(name="erlc_join_leave_log", description="Fetch the latest join/leave logs from erlc server")
async def erlc_join_leave_log(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/joinlogs", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch join logs, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No join/leave logs found.")
        return

    embed = discord.Embed(
        title="{klipbord_emoji} Join/Leave Logs",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    for entry in data:
        ts = entry.get("Timestamp", 0)
        player = entry.get("Player", "Unknown")
        joined = entry.get("Join", True)
        status = "Joined" if joined else "Left"
        embed.add_field(name=f"{status} at {datetime.fromtimestamp(ts, timezone.utc)}", value=player, inline=False)


    await interaction.followup.send(embed=embed)

@bot.tree.command(name="erlc_command_logs", description="Get the list of executed commands")
async def erlc_command_logs(interaction: discord.Interaction): 
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/commandlogs", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch command logs, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No command logs found.")
        return

    embed = discord.Embed(
        title="{clipbord_emoji} Command Logs",
        color=discord.Color.blue(),
        timestamp = datetime.now(timezone.utc)
    )
    for log in data:
        embed.add_field(name=log.get("Command", "Unknown"), value=f"Executed by: {log.get('User', 'Unknown')}", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="roblox_user_info", description="Get public info about a Roblox user by ID")
@app_commands.describe(user_id="The Roblox User ID to fetch info for")
async def roblox_user_info(interaction: discord.Interaction, user_id: str):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        # Get basic user info
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
            if resp.status != 200:
                await interaction.followup.send(f"{failed_emoji} Failed to fetch Roblox user. Status: {resp.status}")
                return
            user_data = await resp.json()

        # Get status
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}/status") as resp2:
            status_data = await resp2.json() if resp2.status == 200 else {}

        # Avatar thumbnail (headshot) and full avatar image
        headshot_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=150&height=150&format=png"
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"

        # Get avatar image URL from the thumbnails API
        async with session.get(avatar_url) as avatar_resp:
            avatar_json = await avatar_resp.json()
            avatar_img_url = avatar_json['data'][0]['imageUrl'] if avatar_resp.status == 200 and avatar_json['data'] else None

        # Build embed
        embed = discord.Embed(
            title="👤 Roblox User Info",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Username", value=user_data.get("name", "Unknown"), inline=True)
        embed.add_field(name="Display Name", value=user_data.get("displayName", "Unknown"), inline=True)
        embed.add_field(name="User ID", value=str(user_data.get("id", "Unknown")), inline=True)
        embed.add_field(name="Description", value=user_data.get("description", "None"), inline=False)
        embed.add_field(name="Created", value=user_data.get("created", "Unknown"), inline=False)
        embed.add_field(name="Status", value=status_data.get("status", "None"), inline=False)

        embed.set_thumbnail(url=headshot_url)
        if avatar_img_url:
            embed.set_image(url=avatar_img_url)

        await interaction.followup.send(embed=embed)











async def get_roblox_usernames(ids: list[int]) -> dict[int, str]:
    usernames = {}
    async with aiohttp.ClientSession() as session:
        for user_id in ids:
            async with session.get(f"{ROBLOX_USER_API}/{user_id}") as res:
                if res.status == 200:
                    data = await res.json()
                    usernames[user_id] = data.get("name", f"ID:{user_id}")
                else:
                    usernames[user_id] = f"ID:{user_id}"
    return usernames

class InfoView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, embed_callback):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.embed_callback = embed_callback

        self.add_item(discord.ui.Button(
            label="🔗 Join Server",
            style=discord.ButtonStyle.link,
            url="https://policeroleplay.community/join?code=SWATxRP&placeId=2534724415"
        ))

    @discord.ui.button(label="🔁 Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("{error_emoji} You can't use this button.", ephemeral=True)
            return

        embed = await self.embed_callback()
        await interaction.response.edit_message(embed=embed)

async def create_server_info_embed(interaction: discord.Interaction) -> discord.Embed:
    global session
    if session is None:
        raise Exception("HTTP session not initialized")

    headers = {"server-key": API_KEY, "Accept": "*/*"}
    async with session.get(f"{API_BASE}", headers=headers) as res:
        if res.status != 200:
            raise Exception("Failed to fetch server data.")
        server = await res.json()

    async with session.get(f"{API_BASE}/players", headers=headers) as res:
        players = await res.json()

    async with session.get(f"{API_BASE}/queue", headers=headers) as res:
        queue = await res.json()

    owner_id = server["OwnerId"]
    co_owner_ids = server.get("CoOwnerIds", [])
    usernames = await get_roblox_usernames([owner_id] + co_owner_ids)

    mods = [p for p in players if p.get("Permission") == "Server Moderator"]
    admins = [p for p in players if p.get("Permission") == "Server Administrator"]
    staff = [p for p in players if p.get("Permission") != "Normal"]

    embed = discord.Embed(
        title=f"{server['Name']} - Server Info",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f"{clipboard_emoji} Basic Info",
        value=(
            f"> **Join Code:** [{server['JoinKey']}](https://policeroleplay.community/join/{server['JoinKey']})\n"
            f"> **Players:** {server['CurrentPlayers']}/{server['MaxPlayers']}\n"
            f"> **Queue:** {len(queue)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"{clipboard_emoji} Staff Info",
        value=(
            f"> **Moderators:** {len(mods)}\n"
            f"> **Administrators:** {len(admins)}\n"
            f"> **Staff in Server:** {len(staff)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"{owner_emoji} Server Ownership",
        value=(
            f"> **Owner:** [{usernames[owner_id]}](https://roblox.com/users/{owner_id}/profile)\n"
            f"> **Co-Owners:** {', '.join([f'[{usernames[uid]}](https://roblox.com/users/{uid}/profile)' for uid in co_owner_ids]) or 'None'}"
        ),
        inline=False
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    return embed

# Add a subcommand to /erlc -> /erlc info
@erlc_group.command(name="info", description="Get ER:LC server info with live data.")
async def erlc_info(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        embed = await create_server_info_embed(interaction)
        view = InfoView(interaction, lambda: create_server_info_embed(interaction))
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"[ERROR] /info command failed: {e}")
        await interaction.followup.send("{failed_emoji} Failed to fetch server information.")



@erlc_group.command(name="players", description="See all players in the server.")
@app_commands.describe(filter="Filter players by username prefix (optional)")
async def players(interaction: discord.Interaction, filter: str = None):
    await interaction.response.defer()

    if session is None:
        await interaction.followup.send("HTTP session not ready.")
        return

    headers = {"server-key": API_KEY}

    # Fetch players
    try:
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"{failed_emoji} Failed to fetch players (status {resp.status})")
                return
            players_data = await resp.json()
    except Exception as e:
        await interaction.followup.send(f"{failed_emoji} Error fetching players: `{e}`")
        return

    # Fetch queue
    try:
        async with session.get(f"{API_BASE}/queue", headers=headers) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"{failed_emoji} Failed to fetch queue (status {resp.status})")
                return
            queue_data = await resp.json()
    except Exception as e:
        await interaction.followup.send(f"{failed_emoji} Error fetching queue: `{e}`")
        return

    staff = []
    actual_players = []

    for p in players_data:
        try:
            username, id_str = p["Player"].split(":")
            player_id = int(id_str)
        except (ValueError, KeyError):
            continue

        permission = p.get("Permission", "Normal")
        team = p.get("Team", "")

        if filter and not username.lower().startswith(filter.lower()):
            continue

        player_info = {
            "username": username,
            "id": player_id,
            "team": team,
        }

        if permission == "Normal":
            actual_players.append(player_info)
        else:
            staff.append(player_info)

    def format_players(players_list):
        if not players_list:
            return "> No players in this category."
        return ", ".join(
            f"[{p['username']} ({p['team']})](https://roblox.com/users/{p['id']}/profile)"
            for p in players_list
        )

    embed = discord.Embed(
        title="SWAT Roleplay Community - Players",
        color=discord.Color.blue()
    )
    embed.description = (
        f"**Server Staff ({len(staff)})**\n"
        f"{format_players(staff)}\n\n"
        f"**Online Players ({len(actual_players)})**\n"
        f"{format_players(actual_players)}\n\n"
        f"**Queue ({len(queue_data)})**\n"
        f"{'> No players in queue.' if not queue_data else ', '.join(str(qid) for qid in queue_data)}"
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.followup.send(embed=embed)


def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            member = await interaction.guild.fetch_member(interaction.user.id)
        if any(role.id == staff_role_id for role in member.roles):
            return True
        raise app_commands.CheckFailure("{failed_emoji} You do not have permission to use this command.")
    return app_commands.check(predicate)

async def get_server_players():
    global session
    if session is None:
        return []
    url = f"{API_BASE}/players"
    headers = {"server-key": API_KEY}
    async with session.get(url, headers=headers) as resp:
        return await resp.json() if resp.status == 200 else []

@erlc_group.command(name="teams", description="See all players grouped by team.")
@is_staff()
@app_commands.describe(filter="Filter players by username prefix (optional)")
async def teams(interaction: discord.Interaction, filter: typing.Optional[str] = None):
    await interaction.response.defer()
    players = await get_server_players()
    teams = {}

    for plr in players:
        if ":" not in plr.get("Player", ""):
            continue
        username, userid = plr["Player"].split(":", 1)

        if filter and not username.lower().startswith(filter.lower()):
            continue

        team = plr.get("Team", "Unknown") or "Unknown"
        teams.setdefault(team, []).append({"username": username, "id": userid})

    team_order = ["Police", "Sheriff", "Fire", "DOT", "Civilian", "Jail"]
    embed_desc = ""

    for team in team_order:
        count = len(teams.get(team, []))
        embed_desc += f"**{team}** {count}\n\n"

    embed = discord.Embed(title="Server Players by Team", description=embed_desc, color=discord.Color.blue())
    embed.set_footer(text="SWAT Roleplay Community")
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.followup.send(embed=embed)

def apply_footer(embed, guild):
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")
    return embed

# ========== /erlc vehicles ==========
@erlc_group.command(name="vehicles", description="Show vehicles currently in the server")
async def vehicles(interaction: discord.Interaction):
    await interaction.response.defer()
    global session
    try:
        headers = {"server-key": API_KEY, "Accept": "*/*"}

        async with session.get(f"{API_BASE}/players", headers=headers) as resp_players:
            if resp_players.status != 200:
                text = await resp_players.text()
                raise Exception(f"PRC API error {resp_players.status}: {text}")
            players = await resp_players.json()

        async with session.get(f"{API_BASE}/vehicles", headers=headers) as resp_vehicles:
            if resp_vehicles.status != 200:
                text = await resp_vehicles.text()
                raise Exception(f"PRC API error {resp_vehicles.status}: {text}")
            vehicles = await resp_vehicles.json()

    except Exception as e:
        return await interaction.followup.send(f"Error fetching or processing vehicles: {get_error_message(e)}")

    if not vehicles:
        embed = discord.Embed(
            title="Server Vehicles 0",
            description="> There are no active vehicles in your server.",
            color=discord.Color.blue()
        )
        embed = apply_footer(embed, interaction.guild)
        return await interaction.followup.send(embed=embed)

    players_dict = {p['Player'].split(":")[0]: p for p in players}
    matched = []

    for vehicle in vehicles:
        owner = vehicle.get("Owner")
        if not owner or owner not in players_dict:
            continue
        matched.append((vehicle, players_dict[owner]))

    matched.sort(key=lambda x: x[1]['Player'].split(":")[0].lower())

    description_lines = []
    for veh, plr in matched:
        username, roblox_id = plr['Player'].split(":", 1)
        description_lines.append(f"[{username}](https://roblox.com/users/{roblox_id}/profile) - {veh['Name']} **({veh['Texture']})**")

    embed = discord.Embed(
        title=f"Server Vehicles [{len(vehicles)}/{len(players)}]",
        description="\n".join(description_lines),
        color=discord.Color.blue()
    )
    embed = apply_footer(embed, interaction.guild)
    await interaction.followup.send(embed=embed)

# ========== /discord check ==========
@discord_group.command(name="check", description="Check if players in ER:LC are not in Discord")
async def check(interaction: discord.Interaction):
    await interaction.response.defer()
    global session

    def extract_roblox_name(name: str) -> str:
        return name.split(" | ", 1)[1].lower() if " | " in name else name.lower()

    try:
        headers = {"server-key": API_KEY, "Accept": "*/*"}
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"PRC API error {resp.status}: {text}")
            players = await resp.json()
    except Exception as e:
        return await interaction.followup.send(f"Error fetching PRC data: {get_error_message(e)}")

    if not players:
        embed = discord.Embed(
            title="No Players in ER:LC",
            description="> No players found in the server.",
            color=discord.Color.blue()
        )
        embed = apply_footer(embed, interaction.guild)
        return await interaction.followup.send(embed=embed)

    roblox_names_in_discord = set()
    for member in interaction.guild.members:
        for name_source in (member.name, member.display_name):
            roblox_names_in_discord.add(extract_roblox_name(name_source))

    missing_players = []
    for player in players:
        roblox_username, roblox_id = player['Player'].split(":", 1)
        if roblox_username.lower() not in roblox_names_in_discord:
            missing_players.append((roblox_username, roblox_id))

    description = (
        "> All players are in the Discord server."
        if not missing_players else
        "\n".join(f"> [{u}](https://roblox.com/users/{i}/profile)" for u, i in missing_players)
    )

    embed = discord.Embed(
        title="Players in ER:LC Not in Discord",
        description=description,
        color=discord.Color.blue()
    )
    embed = apply_footer(embed, interaction.guild)
    await interaction.followup.send(embed=embed)

# Close aiohttp session on exit
@atexit.register
def close_session():
    if session and not session.closed:
        bot.loop.run_until_complete(session.close())

# ===== Embed Helpers =====

def success_embed(title, desc, guild):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.green())
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")
    return embed

def error_embed(title, desc, guild):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.red())
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")
    return embed

def is_staff():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_guild
    return app_commands.check(predicate)

@erlc_group.command(name="bans", description="Filter the bans of your server.")
@is_staff()
@app_commands.describe(username="Filter by Roblox username", user_id="Filter by Roblox user ID")
async def bans(
    interaction: discord.Interaction,
    username: typing.Optional[str] = None,
    user_id: typing.Optional[int] = None,
):
    await interaction.response.defer()

    url = "https://api.policeroleplay.community/v1/server/bans"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title="PRC API Error",
                        description=f"{error_emoji} Failed to fetch bans. Status code: {resp.status}",
                        color=discord.Color.blurple(),  # or your BLANK_COLOR
                    )
                )
            bans_data = await resp.json()  # dict: {PlayerId: PlayerName}

    embed = discord.Embed(color=discord.Color.blurple(), title="Bans", description="")
    status = username or user_id

    username_filter = username.lower() if username else None
    user_id_filter = str(user_id) if user_id else None

    old_embed = copy.copy(embed)
    embeds = [embed]

    for player_id, player_name in bans_data.items():
        if (username_filter and username_filter in player_name.lower()) or (user_id_filter and user_id_filter == player_id) or not status:
            embed = embeds[-1]
            if len(embed.description) > 3800:
                new_embed = copy.copy(old_embed)
                embeds.append(new_embed)
                embed = new_embed
            embed.description += f"> [{player_name} ({player_id})](https://roblox.com/users/{player_id}/profile)\n"

    if embeds[0].description.strip() == "":
        embeds[0].description = (
            "> This ban was not found."
            if status
            else "> No bans found on your server."
        )

    guild_icon = interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None
    for embed in embeds:
        embed.set_author(name=interaction.guild.name, icon_url=guild_icon)
        if guild_icon:
            embed.set_thumbnail(url=guild_icon)
        embed.set_footer(text="SWAT Roleplay Community")

    for embed in embeds:
        await interaction.followup.send(embed=embed)

def roblox_link(player_str: str):
    """Returns [Name](link) or just name if format is invalid."""
    try:
        name, user_id = player_str.split(":")
        return f"[{name}](https://www.roblox.com/users/{user_id}/profile)"
    except ValueError:
        return player_str

async def fetch_modcalls():
    url = f"{API_BASE}/modcalls"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(f"Failed to fetch modcalls: HTTP {resp.status}")

async def fetch_killlogs():
    url = f"{API_BASE}/killlogs"
    headers = {
        "server-key": API_KEY,
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(f"Failed to fetch kill logs: HTTP {resp.status}")

@erlc_group.command(name="killlogs", description="Show recent kill logs")
async def killlogs(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        killlogs = await fetch_killlogs()

        embed = discord.Embed(
            title="SWAT Roleplay Community - Kill Logs",
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="SWAT Roleplay Community")

        if not killlogs:
            embed.add_field(
                name="No Kill Logs Found",
                value="> No kills in this category.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        for entry in killlogs[:10]:
            killer = roblox_link(entry.get("Killer", "Unknown"))
            victim = roblox_link(entry.get("Victim", "Unknown"))
            weapon = entry.get("Weapon", "Unknown")
            timestamp = entry.get("Timestamp", 0)
            time_str = f"<t:{int(timestamp)}:R>"

            value_text = (
                f"> **Killer:** {killer}\n"
                f"> **Victim:** {victim}\n"
                f"> **Weapon:** `{weapon}`\n"
                f"> **Time:** {time_str}"
            )

            embed.add_field(
                name="\u200b",
                value=value_text,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch kill logs.\n{e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)


@erlc_group.command(name="modcalls", description="Show recent moderator call logs")
async def modcalls(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        modcalls = await fetch_modcalls()

        embed = discord.Embed(
            title="SWAT Roleplay Community - Modcalls",
            color=discord.Color.blue()
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.set_footer(text="SWAT Roleplay Community")

        if not modcalls:
            embed.add_field(
                name="No Modcalls Found",
                value="> No modcalls in this category.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return

        for entry in modcalls[:10]:
            caller = roblox_link(entry.get("Caller", "Unknown"))
            moderator_raw = entry.get("Moderator", "No responder")
            moderator = roblox_link(moderator_raw) if ":" in moderator_raw else moderator_raw
            timestamp = entry.get("Timestamp", 0)
            time_str = f"<t:{int(timestamp)}:R>"

            value_text = (
                f"> **Caller:** {caller}\n"
                f"> **Moderator:** {moderator}\n"
                f"> **Time:** {time_str}"
            )

            embed.add_field(
                name="\u200b",
                value=value_text,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch modcalls.\n{e}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

def has_staff_role(member: discord.Member) -> bool:
    return any(role.id == OWNER_ID for role in member.roles)

command_CHANNEL_ID = 1343303552604569690
last_shutdown_call = 0  # cooldown timestamp


async def send_command(channel: discord.TextChannel, command_json: dict, waiting: float, 
                       success_title: str, waiting_desc: str, no_players_title: str, no_players_desc: str):
    global session
    try:
        async with session.post(f"{API_BASE}/command", headers=HEADERS_POST, json=command_json) as resp:
            if resp.status == 200:
                embed = discord.Embed(title=success_title, description=waiting_desc, color=discord.Color.green())
                await channel.send(embed=embed)
            elif resp.status == 422:
                embed = discord.Embed(title=no_players_title, description=no_players_desc, color=discord.Color.gold())
                await channel.send(embed=embed)
                return False
            else:
                text = await resp.text()
                embed = discord.Embed(title="Failed to Send Command {failed_emoji}",
                                      description=f"API responded with status code `{resp.status}`:\n{text}",
                                      color=discord.Color.red())
                await channel.send(embed=embed)
                return False
    except Exception as e:
        embed = discord.Embed(title="Error Sending Command {failed_emoji}", description=f"Exception: `{e}`", color=discord.Color.red())
        await channel.send(embed=embed)
        return False

    await asyncio.sleep(waiting)
    return True


async def send_ssd_and_kick(channel: discord.TextChannel):
    global last_shutdown_call
    if time.time() - last_shutdown_call < 5:
        return  # cooldown 5 seconds
    last_shutdown_call = time.time()

    shutdown_msg = {
        "command": ":m ❗ SWAT Roleplay Community has unfortunately chosen to SSD. You must leave the game at this time and only rejoin during an SSU. Failure to leave within 3 minutes will result in being kicked. If you have any questions, call !mod. Thank you! ❗"
    }
    kick_msg = {"command": ":kick all"}

    sent = await send_command(
        channel, shutdown_msg, 240,
        "SSD Message Sent ✅",
        "The shutdown message was successfully sent. Waiting 4 minutes before kicking all players...",
        "No Players in Server ⚠️",
        "There are no players currently in the server to receive the SSD message."
    )
    if not sent:
        return

    # After 4 minutes, kick all
    await send_command(
        channel, kick_msg, 0,
        "Kick All Sent ✅",
        "",
        "No Players to Kick ⚠️",
        "Kick all failed — no players were left in the server."
    )


@bot.tree.command(name="ssd", description="Send a server shutdown message to the ER:LC server")
async def ssd(interaction: discord.Interaction):
    await interaction.response.defer()
    await send_ssd_and_kick(interaction.channel)


@bot.event
async def on_message(message: discord.Message):
    global last_shutdown_call

    if message.channel.id != command_CHANNEL_ID:
        await bot.process_commands(message)
        return

    if message.webhook_id and message.embeds:
        embed = message.embeds[0]
        if embed.description and ":log ssd" in embed.description.lower():
            if time.time() - last_shutdown_call < 5:
                return
            await send_ssd_and_kick(message.channel)

    await bot.process_commands(message)


async def send_emergency_shutdown_message(channel: discord.TextChannel):
    shutdown_msg = {
        "command": ":m ❗ The SWAT Roleplay Community owner has done an emergency server shutdown. You must leave the game. Failure to leave within 1.5 minutes will result in being kicked. Thank you! ❗"
    }
    kick_msg = {"command": ":kick all"}

    sent = await send_command(
        channel, shutdown_msg, 90,
        "Emergency SSD Message Sent {tick_emoji}",
        "The emergency shutdown message was successfully sent. Waiting 1.5 minutes before kicking all players...",
        "No Players in Server {failed_emoji}",
        "There are no players currently in the server to receive the emergency shutdown message."
    )
    if not sent:
        return

    await send_command(
        channel, kick_msg, 0,
        "Kick All Sent {tick_emoji}",
        "",
        "No Players to Kick {failed_emoji}",
        "Kick all failed — no players were left in the server."
    )


@erlc_group.command(name="shutdown", description="Send a server shutdown message to the ER:LC server")
async def shutdown_erlc(interaction: discord.Interaction):
    member = interaction.guild.get_member(interaction.user.id)
    if not member or not has_staff_role(member):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Permission Denied {failed_emoji}",
                description="You must have the Staff role to use this command.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await send_emergency_shutdown_message(interaction.channel)


# --- PRC API HANDLING ---

def get_join_logs():
    try:
        res = requests.get(f"{API_BASE}/joinlogs", headers={"server-key": API_KEY})
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Join log fetch error: {e}")
    return []

def send_welcome(player_name):
    command = f":pm {player_name} {WELCOME_TEMPLATE}"
    res = requests.post(
        f"{API_BASE}/command",
        headers={"server-key": API_KEY, "Content-Type": "application/json"},
        json={"command": command}
    )
    return res.status_code == 200

def kick_user(player_id):
    command = f":kick {player_id} {KICK_REASON}"
    res = requests.post(
        f"{API_BASE}/command",
        headers={"server-key": API_KEY, "Content-Type": "application/json"},
        json={"command": command}
    )
    return res.status_code == 200

def fetch_command_logs():
    global last_checked_time
    try:
        res = requests.get(f"{API_BASE}/commandlogs", headers={"server-key": API_KEY})
        if res.status_code != 200:
            return []

        logs = res.json()
        new_logs = [
            log for log in logs
            if log["Timestamp"] > last_checked_time and log["Command"].startswith(":log vc")
        ]
        if new_logs:
            last_checked_time = max(log["Timestamp"] for log in new_logs)
        return new_logs
    except Exception as e:
        print(f"Error fetching command logs: {e}")
        return []

# --- DISCORD BOT EVENTS ---

@tasks.loop(seconds=60)
async def process_joins_loop():
    logs = get_join_logs()
    for log in logs:
        if not log["Join"]:
            continue
        player_raw = log["Player"]  # e.g., PlayerName:123456
        player_name = player_raw.split(":")[0]

        if player_name in handled_usernames:
            continue

        if player_name.lower().startswith("all") or player_name.lower().startswith("others"):
            if kick_user(player_name):
                print(f"⛔ Kicked {player_name} for restricted username.")
            else:
                print(f"{failed_emoji} Failed to kick {player_name}.")
        else:
            if player_name not in welcomed_players:
                if send_welcome(player_name):
                    print(f"{tick_emoji} Welcomed {player_name}")
                    welcomed_players.add(player_name)
                else:
                    print(f"{failed_emoji} Failed to welcome {player_name}")

        handled_usernames.add(player_name)

@tasks.loop(seconds=100)
async def check_log_commands():
    logs = fetch_command_logs()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("{failed_emoji} Guild not found")
        return

    for log in logs:
        command = log["Command"]
        roblox_username = log["Player"].split(":")[0]

        match = re.match(r":log vc\s+(\S+)(?:\s+(\S+))?", command)
        if not match:
            continue

        if match.group(2):  # :log vc user abbrev
            target_username = match.group(1)
            abbrev = match.group(2).upper()
        else:  # :log vc abbrev
            target_username = roblox_username
            abbrev = match.group(1).upper()

        vc_id = VC_ABBREVIATIONS.get(abbrev)
        if not vc_id:
            print(f"{failed_emoji} Invalid VC abbreviation: {abbrev}")
            continue

        discord_id = ROBLOX_TO_DISCORD.get(target_username)
        if not discord_id:
            print(f"{error_emoji} No Discord user linked for {target_username}")
            continue

        member = guild.get_member(discord_id)
        if not member:
            print(f"{failed_emoji} Member not in guild: {discord_id}")
            continue

        if not member.voice or not member.voice.channel:
            print(f"ℹ️ {member.display_name} not in VC")
            continue

        try:
            await member.move_to(guild.get_channel(vc_id))
            print(f"{tick_emoji} Moved {member.display_name} to {abbrev}")
        except Exception as e:
            print(f"{failed_emoji} Failed to move {member.display_name}: {e}")

@tasks.loop(seconds=400)
async def update_vc_status():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    headers = {"server-key": API_KEY}

    # Get player count
    try:
        player_response = requests.get(f"{API_BASE}", headers=headers)
        player_count = player_response.json().get("CurrentPlayers", 0)
    except Exception as e:
        print("{failed_emoji} Failed to fetch player count:", e)
        player_count = 0

    # Get queue count
    try:
        queue_response = requests.get(f"{API_BASE}/queue", headers=headers)
        queue_count = len(queue_response.json()) if queue_response.status_code == 200 else 0
    except Exception as e:
        print("{failed_emoji} Failed to fetch queue:", e)
        queue_count = 0

    # Rename VCs
    try:
        player_vc = guild.get_channel(PLAYERCOUNT_VC_ID)
        queue_vc = guild.get_channel(QUEUE_VC_ID)

        if player_vc:
            await player_vc.edit(name=f"{PLAYERCOUNT_PREFIX} {player_count}")
        if queue_vc:
            await queue_vc.edit(name=f"{QUEUE_PREFIX} {queue_count}")
    except Exception as e:
        print("{failed_emoji} Failed to update VC names:", e)

async def check_vehicle_restrictions(bot):
    headers = {"server-key": "YOUR_SERVER_KEY"}
    try:
        response = requests.get("https://api.policeroleplay.community/v1/server/vehicles", headers=headers)
        vehicles = response.json()
    except Exception as e:
        print("{failed_emoji} Failed to fetch vehicle list:", e)
        return

    for vehicle in vehicles:
        vehicle_name = vehicle["Name"]
        player_name = vehicle["Owner"]

        if vehicle_name not in RESTRICTED_VEHICLES:
            continue

        discord_user_id = ROBLOX_DISCORD_LINKS.get(player_name)
        if not discord_user_id:
            print(f"🔍 No Discord link for {player_name}")
            continue

        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(discord_user_id)

        if not member:
            print(f"{failed_emoji} Member not found in Discord: {player_name}")
            continue

        allowed_roles = RESTRICTED_VEHICLES[vehicle_name]
        if not any(role.id in allowed_roles for role in member.roles):
            # Not allowed – send warning or kick
            warn_command = f":m {player_name}, you are not allowed to use the {vehicle_name}!"
            requests.post(
                "https://api.policeroleplay.community/v1/server/command",
                headers=headers,
                json={"command": warn_command}
            )
            print(f"{tick_emoji} Warned {player_name} for unauthorized vehicle use.")

@bot.tree.command(name="set_restriction")
@app_commands.describe(vehicle="Vehicle name", role="Role required")
async def set_restriction(interaction: discord.Interaction, vehicle: str, role: discord.Role):
    RESTRICTED_VEHICLES[vehicle] = [role.id]
    await interaction.response.send_message(f"{tick_emoji} Set restriction: `{vehicle}` → `{role.name}`", ephemeral=True)

@tasks.loop(seconds=30)  # every 30 seconds, or adjust as you want
async def check_staff_livery():
    headers = {"server-key": API_KEY}
    try:
        resp = requests.get({API_BASE}/vehicles, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch vehicles: {resp.status_code}")
            return
        
        vehicles = resp.json()
        
        # Filter vehicles with "STAFF TEAM" or "STAFF TEAM 2" in Texture or Name
        staff_vehicles = [v for v in vehicles if v.get("Texture", "").upper() in ("STAFF TEAM", "STAFF TEAM 2") or v.get("Name", "").upper() in ("STAFF TEAM", "STAFF TEAM 2")]
        
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if not channel:
            print("{error_emoji} Channel not found")
            return
        
        for vehicle in staff_vehicles:
            owner_name = vehicle.get("Owner")
            if not owner_name:
                continue
            
            # Try to find the Discord Member with matching username (or better, map Roblox to Discord some way)
            # This is tricky without a direct mapping - for demonstration, we assume Discord username == Owner name
            guild = channel.guild
            member = discord.utils.find(lambda m: m.name == owner_name, guild.members)
            if not member:
                # Could not find the user in the guild - skip or log
                continue
            
            # Skip if member has the staff role
            if any(role.id == staff_role_id for role in member.roles):
                continue
            
            # Send embed message to channel
            embed = discord.Embed(
                title="Staff Livery Detected",
                description=f"User **{owner_name}** is using a staff vehicle livery!",
                color=discord.Color.red()
            )
            embed.add_field(name="Vehicle Name", value=vehicle.get("Name", "Unknown"), inline=True)
            embed.add_field(name="Texture", value=vehicle.get("Texture", "Unknown"), inline=True)
            embed.set_footer(text="PRC Server Monitor")
            
            # To avoid spamming, you may want to track who you've already notified about recently
            await channel.send(embed=embed)
            
    except Exception as e:
        print(f"Error fetching or processing vehicles: {e}")



async def fetch_players():
    headers = {"server-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

@erlc_group.command(name="callsigns", description="List all players and their callsigns on the ER:LC server")
async def erlc_callsigns(interaction: discord.Interaction):
    await interaction.response.defer()

    players = await fetch_players()
    if players is None:
        embed = discord.Embed(
            title="Error",
            description="Failed to fetch players from the server API.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        await interaction.followup.send(embed=embed)
        return

    if len(players) == 0:
        embed = discord.Embed(
            title="No Players Found",
            description="There are no players currently on the server.",
            color=discord.Color.orange()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        await interaction.followup.send(embed=embed)
        return

    # Build the description listing all players
    description_lines = []
    for p in players:
        player_name = p["Player"].split(":")[0]
        callsign = p.get("Callsign") or "No callsign (civilian)"
        team = p.get("Team") or "Unknown"
        description_lines.append(
            f"**Team:** {team}\n**User:** {player_name}\n**Callsign:** {callsign}\n"
        )

    description = "\n".join(description_lines)

    embed = discord.Embed(
        title="SWAT Roleplay Community - callsigns",
        description=description,
        color=discord.Color.blue()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.followup.send(embed=embed)






GUILD_ID = 1343179590247645205
CATEGORY_ID = 1368337231508406322
STAFF_ROLE_IDS = {1346578198749511700}
TRANSCRIPT_LOG_CHANNEL = 1381267054354632745
STAFF_ROLE_PING = "<@&1346578198749511700>"

active_threads = {}  # user_id: channel_id
claimed_by = {}      # user_id: staff_id

def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9]", "-", name.lower())[:90]

async def get_or_create_thread(user):
    guild = bot.get_guild(GUILD_ID)
    category = guild.get_channel(CATEGORY_ID)
    thread_name = f"modmail-{safe_name(user.name)}"

    existing = discord.utils.get(category.text_channels, topic=f"ID:{user.id}")
    if existing:
        return existing

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
    }

    channel = await guild.create_text_channel(
        name=thread_name,
        category=category,
        topic=f"ID:{user.id}",
        overwrites=overwrites
    )
    active_threads[user.id] = channel.id

    await channel.send(f"{STAFF_ROLE_PING} 📬 New modmail opened by {user.mention} (`{user.id}`)")

    return channel

class ConfirmView(discord.ui.View):
    def __init__(self, user, content):
        super().__init__(timeout=60)
        self.user = user
        self.content = content

    @discord.ui.button(label="📨 Send to Staff", style=discord.ButtonStyle.green)
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This is not your prompt!", ephemeral=True)

        channel = await get_or_create_thread(self.user)

        embed = discord.Embed(
            title="📩 New Modmail Message",
            description=self.content,
            color=discord.Color.blue()
        )
        embed.set_author(name=str(self.user), icon_url=self.user.display_avatar.url)
        embed.set_footer(text=f"User ID: {self.user.id}")
        await channel.send(embed=embed)

        await interaction.response.edit_message(content=f"{tick_emoji} Sent to staff.", view=None)

        await self.user.send("🔒 Use the button below to close this thread when done.", view=CloseView(self.user.id))

class CloseView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🔒 Close Thread", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_id = active_threads.get(self.user_id)
        if not channel_id:
            return await interaction.response.send_message("Thread not found.", ephemeral=True)

        guild = bot.get_guild(GUILD_ID)
        channel = guild.get_channel(channel_id)

        await channel.send("🛑 User closed the thread.")
        await send_transcript(channel, self.user_id)
        del active_threads[self.user_id]
        await interaction.response.send_message(f"{tick_emoji} Closed. Thank you!")

async def send_transcript(channel, user_id):
    output = ""
    async for msg in channel.history(limit=None, oldest_first=True):
        output += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

    transcript_file = discord.File(io.BytesIO(output.encode()), filename="transcript.txt")
    log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)
    user = await bot.fetch_user(user_id)

    if log_channel:
        await log_channel.send(f"{clipboard_emoji} Transcript for user `{user}`", file=transcript_file)

    try:
        await user.send(f"{clipboard_emoji} Here's the transcript of your modmail session:", file=transcript_file)
    except discord.Forbidden:
        # User has DMs off or blocked the bot
        if log_channel:
            await log_channel.send(f"{error_emoji} Could not DM transcript to `{user}` — DMs are closed.")
    except discord.HTTPException as e:
        # Some other issue occurred during the DM
        if log_channel:
            await log_channel.send(f"{failed_emoji} Failed to send transcript to `{user}`: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild is None:
        user = message.author
        if user.id in active_threads:
            guild = bot.get_guild(GUILD_ID)
            channel = guild.get_channel(active_threads[user.id])
        else:
            channel = None

        if not channel:
            await message.channel.send(
                embed=discord.Embed(
                    title="Send to Staff?",
                    description=message.content,
                    color=discord.Color.orange()
                ),
                view=ConfirmView(user, message.content)
            )
            return

        embed = discord.Embed(description=message.content, color=discord.Color.green())
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        await channel.send(embed=embed)
    else:
        topic = message.channel.topic
        if topic and topic.startswith("ID:") and message.author.id != bot.user.id:
            user_id = int(topic.replace("ID:", ""))
            try:
                user = await bot.fetch_user(user_id)
                embed = discord.Embed(description=message.content, color=discord.Color.purple())
                embed.set_author(name=f"Staff: {message.author}")
                await user.send(embed=embed)
            except Exception as e:
                await message.channel.send(f"{failed_emoji} Could not message user: {e}")

# ========== Slash Commands ==========
@bot.tree.command(name="claim", description="Claim this modmail thread.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def claim(interaction: discord.Interaction):
    topic = interaction.channel.topic
    if not topic or not topic.startswith("ID:"):
        return await interaction.response.send_message(f"{failed_emoji} Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))
    user = await bot.fetch_user(user_id)

    claimed_by[user_id] = interaction.user.id
    await interaction.response.send_message(f"{tick_emoji} Claimed by {interaction.user.mention}")

    try:
        await user.send(f"👮 Your modmail was claimed by {interaction.user.name}.")
    except discord.Forbidden:
        # User has DMs off or blocked the bot
        log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)  # Optional: log somewhere
        if log_channel:
            await log_channel.send(f"{error_emoji} Could not DM user `{user}` about the claim — DMs are disabled.")
    except discord.HTTPException as e:
        # Any other DM failure
        log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(f"{failed_emoji} Failed to send claim DM to `{user}`: {e}")


@bot.tree.command(name="close", description="Close and archive this thread.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def close(interaction: discord.Interaction):
    topic = interaction.channel.topic
    if not topic or not topic.startswith("ID:"):
        return await interaction.response.send_message(f"{failed_emoji} Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))

    await interaction.response.send_message("🔒 Closing thread...")
    await interaction.channel.send("🔒 Closed by staff.")

    try:
        user = await bot.fetch_user(user_id)
        await user.send("🔒 Your modmail thread has been closed by staff.")
    except discord.Forbidden:
        log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(f"{error_emoji} Could not DM user `{user_id}` — DMs are disabled.")
    except discord.HTTPException as e:
        log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(f"{failed_emoji} Failed to send close DM to `{user_id}`: {e}")

    if user_id in active_threads:
        del active_threads[user_id]


@bot.tree.command(name="delete", description="Delete this modmail channel.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def delete(interaction: discord.Interaction):
    await interaction.response.send_message("🗑 Deleting channel...", ephemeral=True)
    await interaction.channel.delete()

@bot.tree.command(name="transcript", description="Get transcript of this thread.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def transcript(interaction: discord.Interaction):
    topic = interaction.channel.topic
    if not topic or not topic.startswith("ID:"):
        return await interaction.response.send_message(f"{failed_emoji} Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))
    await send_transcript(interaction.channel, user_id)
    await interaction.response.send_message(f"{clipboard_emoji} Transcript sent.")





# Remove the default help command so we can define our own
bot.remove_command("help")

# ------------------------ Help Slash Command ------------------------

@bot.tree.command(name="help", description="Show all available commands and their descriptions")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands List",
        description="Explore the available commands grouped by category. Use </command:1381009162334503014> for more details.",
        color=discord.Color.blurple()
    )

    # Add categorized fields
    embed.add_field(name="**🛠️ General**", value="</ping:1381009161621475383> - Check if the bot is online\n</say:1381009161621475384> - Let the bot say something\n</embed:1381009161621475387> - Create a custom embed message\nUse </command:1381009162334503014> for more details.", inline=False)
    embed.add_field(name="**⚙️ Moderation**", value="</slowmode:1381009161621475385> - Set slowmode\n</clear:1381009162170929406> - Clear messages\n</nickname:1381009161814540386> - Change nickname\n</warn:1381009161621475378>, </warnings:1381009161621475380>, </unwarn:1381009161621475379>, </clear_all_warnings:1381009161621475382>\n</shutdown:1381278435938271296> - Shutdown\n</kick:1381009161961078864>, </ban:1381009161961078865>, </unban:1381009162170929405>, </mute:1381009161961078866>, </unmute:1381009162170929404>\nUse </command:1381009162334503014>.", inline=False)
    embed.add_field(name="**🚨 ER:LC Management**", value="</session vote:1381009161961078863> - ER:LC vote command\nUse </command:1381009162334503014>.", inline=False)
    embed.add_field(name="**🔒 Channel Management**", value="</lock:1381009162170929408>, </unlock:1381009162170929407>\nUse </command:1381009162334503014>.", inline=False)
    embed.add_field(name="**⏰ AFK Management**", value="</afk:1381009161814540380>, </unafk:1381009161814540381>\nUse </command:1381009162334503014>.", inline=False)
    embed.add_field(name="**💼 Other (Part 1)**", value="</roleinfo:1381009161814540384>, </invite:1381009161814540385>, </server_info:1381009161814540382>, </user_info:1381009161814540383>, </remindme:1381009161814540388>, </servericon:1381009161814540387>, </suggestion:1381009161814540389>, </staff_suggestion:1381009161961078857>, </staff_feedback:1381009161961078858>, </events:1381009161961078861>", inline=False)
    embed.add_field(name="**💼 Other (Part 2)**", value="</event:1381009161961078860>, </mod_panel:1381009161961078862>, </report:1381009162170929409>, </poll:1381009162170929410>, </setreportticket:1381009162170929412>, </settickets:1381009162170929411>, </up_time:1381009161621475386>, </dm:1381005826558267392>\nUse </command:1381009162334503014>.", inline=False)

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="The SWAT Roleplay Community | Use /command [command name] for more details.")

    await interaction.response.send_message(embed=embed)

# ------------------------ Help Prefix Command ------------------------

@bot.command(name="help", description="Show all available commands and their descriptions")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="Bot Commands List",
        description="Explore the available commands grouped by category. Use `/command [command name]` for more details.",
        color=discord.Color.blurple()
    )

    embed.add_field(name="**🛠️ General**", value="`ping`, `say`, `embed`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**⚙️ Moderation**", value="`slowmode`, `clear`, `nickname`, `warn`, `warnings`, `unwarn`, `clear_all_warnings`, `shutdown`, `kick`, `ban`, `unban`, `mute`, `unmute`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**🚨 ER:LC Management**", value="`session vote`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**🔒 Channel Management**", value="`lock`, `unlock`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**⏰ AFK Management**", value="`afk`, `unafk`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**💼 Other (Part 1)**", value="`roleinfo`, `invite`, `server_info`, `user_info`, `remindme`, `servericon`, `suggestion`, `staff_suggestion`, `staff_feedback`, `events`\nUse `/command [command name]`.", inline=False)
    embed.add_field(name="**💼 Other (Part 2)**", value="`event`, `mod_panel`, `report`, `poll`, `setreportticket`, `settickets`, `up_time`, `dm`\nUse `/command [command name]`.", inline=False)

    if ctx.guild and ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text="The SWAT Roleplay Community | Use /command [command name] for more details.")

    await ctx.send(embed=embed)

# ------------------------ Command Detail Slash ------------------------

@bot.tree.command(name="command", description="Get detailed help for a specific command")
async def command_help_slash(interaction: discord.Interaction, command_name: str):
    await send_command_detail(interaction, command_name)

# ------------------------ Command Detail Prefix ------------------------

@bot.command(name="command", description="Get detailed help for a specific command")
async def command_help_prefix(ctx, command_name: str):
    await send_command_detail(ctx, command_name)

# ------------------------ Command Lookup Helper ------------------------

async def send_command_detail(target, command_name):
    command_name = command_name.lower()
    command_details = {
        "ping": "Ping the bot to check if it's online.",
        "help": "Show all available commands and their descriptions.",
        "command": "Get detailed help for a specific command.",
        "say": "Let the bot repeat a message of your choice.",
        "embed": "Create a custom embed message with specified fields.",
        "slowmode": "Set slowmode in a channel to restrict message frequency.",
        "clear": "Clear a specified number of messages in a channel.",
        "kick": "Kick a member from the server.",
        "ban": "Ban a member from the server.",
        "unban": "Unban a member from the server.",
        "mute": "Mute a member.",
        "unmute": "Unmute a member.",
        "giverole": "Give a role to a member.",
        "removerole": "Remove a role from a member.",
        "muteall": "Mute all members.",
        "unmuteall": "Unmute all members.",
        "lock": "Lock the current channel.",
        "unlock": "Unlock the current channel.",
        "lockdown": "Lock all channels.",
        "stop_lockdown": "Unlock all channels.",
        "afk": "Set yourself as AFK.",
        "unafk": "Remove AFK status.",
        "roleinfo": "Get information about a role.",
        "invite": "Get the bot's invite link.",
        "server_info": "Get server information.",
        "user_info": "Get user information.",
        "poll": "Create a yes/no poll.",
        "remindme": "Set a reminder.",
        "servericon": "Get server icon.",
        "suggestion": "Submit a suggestion.",
        "staff_feedback": "Feedback for a staff member.",
        "events": "View upcoming events.",
        "event": "Create an event.",
        "shutdown": "Shut down the bot (owner only).",
        "clear_all_warnings": "Clear all warnings.",
        "nickname": "Change a user's nickname.",
        "warn": "Warn a user.",
        "warnings": "View warnings.",
        "unwarn": "Remove a warning.",
        "staff_suggestion": "Submit a staff-only suggestion.",
        "mod_panel": "Open moderator tools.",
        "report": "Report a user.",
        "setreportticket": "Send the in-game report ticket buttons.",
        "settickets": "Send support ticket buttons.",
        "up_time": "Show how long the bot has been running.",
        "dm": "Send yourself a DM with an embed editor.",
        "session vote": "Start a vote for ER:LC session."
    }

    matching = [name for name in command_details if command_name in name]

    if len(matching) == 1:
        cmd = matching[0]
        embed = discord.Embed(title=f"Help: /{cmd}", description=command_details[cmd], color=discord.Color.green())
        await (target.send(embed=embed) if isinstance(target, commands.Context) else target.response.send_message(embed=embed))
    elif len(matching) > 1:
        await (target.send(f"Multiple matches found: {', '.join(matching)}.") if isinstance(target, commands.Context) else target.response.send_message(f"Multiple matches found: {', '.join(matching)}."))
    else:
        await (target.send(f"No help found for `{command_name}`.") if isinstance(target, commands.Context) else target.response.send_message(f"No help found for `{command_name}`."))

# ------------------------ End of Help Commands ------------------------

if __name__ == "__main__":
    load_events()
    bot.run(os.getenv("DISCORD_TOKEN"))













