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
from dotenv import load_dotenv
import aiohttp
from datetime import UTC
from collections import defaultdict, deque
from discord.ui import Button, View
from discord import app_commands, ui
import re, io
import datetime
from threading import Thread
from datetime import datetime, timezone
from datetime import timezone
from keep_alive import keep_alive
import typing
import atexit
import copy

keep_alive()  # Starts the web server

UTC = timezone.utc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.basicConfig(filename='error.log', level=logging.ERROR)

load_dotenv()  # This loads the .env file

# Colors
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blue()

# Define intents to specify the events your bot should listen to
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True
intents = discord.Intents.all()





kill_tracker = defaultdict(lambda: deque())

# Create the bot instance with a command prefix and intents
bot = commands.Bot(command_prefix=".", intents=intents)

# Set up the slash command tree
tree = bot.tree

# Global session, created in on_ready
session: aiohttp.ClientSession | None = None

@bot.event
async def on_ready():
    # Add command groups before syncing
    bot.tree.add_command(erlc_group)
    bot.tree.add_command(discord_group)

    # Sync commands
    await bot.tree.sync()  # Global sync
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))  # Guild sync

    bot.start_time = datetime.now(timezone.utc)

    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()

    # Start background tasks
    join_leave_log_task.start()
    kill_log_task.start()
    process_joins_loop.start()
    check_log_commands.start()
    update_vc_status.start()
    check_staff_livery.start()

    # Set presence to DND with a watching status
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    print(f"{bot.user} has connected to Discord and is watching over the server.")
    print("-----------------------------------------------------------------------")


# ---------------------------------------------------------------------------------------------------------

# groups
erlc_group = discord.app_commands.Group(name="erlc", description="Get ER:LC server info with live data.")
discord_group = app_commands.Group(name="discord", description="Discord-related commands")

# ---------------------------------------------------------------------------------------------------------

    

# Replace with your target server's ID
TARGET_SERVER_ID = 1343179590247645205

# Load warnings from the file
def load_warnings():
    try:
        with open('warnings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save warnings to the file
def save_warnings(warnings_data):
    with open('warnings.json', 'w') as f:
        json.dump(warnings_data, f, indent=4)

# Warnings storage
warnings = load_warnings()

# Warn command
@bot.tree.command(name="warn", description="Warn a user for a specific reason")
async def warn_slash(interaction: discord.Interaction, user: discord.Member, reason: str):
    user_id = str(user.id)
    
    # Initialize the user warning list if it doesn't exist
    if user_id not in warnings:
        warnings[user_id] = []

    # Add the new warning to the user's list
    warnings[user_id].append(reason)
    save_warnings(warnings)

    # Send confirmation message
    await interaction.response.send_message(f"{user.mention} has been warned for: {reason}")

# Unwarn command
@bot.tree.command(name="unwarn", description="Remove a specific warning from a user")
async def unwarn_slash(interaction: discord.Interaction, user: discord.Member):
    user_id = str(user.id)

    # Check if the user has any warnings
    if user_id in warnings and warnings[user_id]:
        # Create a select menu to choose a warning to remove
        options = [
            discord.SelectOption(label=f"Warning {i+1}: {warn[:50]}...", value=str(i))
            for i, warn in enumerate(warnings[user_id])
        ]
        
        select = Select(placeholder="Choose a warning to remove", options=options)
        
        # Create a View and send the select menu
        async def select_callback(interaction: discord.Interaction):
            warning_index = int(select.values[0])
            removed_warning = warnings[user_id].pop(warning_index)  # Remove the selected warning
            save_warnings(warnings)

            embed = discord.Embed(
                title="Warning Removed",
                description=f"Removed the warning: {removed_warning} from {user.mention}.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Action taken by {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)

        select.callback = select_callback
        view = View()
        view.add_item(select)

        await interaction.response.send_message(
            f"Select the warning you want to remove from {user.mention}:",
            view=view
        )
    else:
        # Send failure message if no warnings exist
        embed = discord.Embed(
            title="No Warnings Found",
            description=f"{user.mention} has no warnings to remove.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

# Warnings command
@bot.tree.command(name="warnings", description="Show all warnings for a user")
async def warnings_slash(interaction: discord.Interaction, user: discord.Member):
    user_id = str(user.id)

    # Check if the user has any warnings
    if user_id in warnings and warnings[user_id]:
        warning_list = "\n".join(f"{i+1}. {warn}" for i, warn in enumerate(warnings[user_id]))
        
        # Send warning list in an embed
        embed = discord.Embed(
            title=f"Warnings for {user.display_name}",
            description=warning_list,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
    else:
        # Send no warnings message in an embed
        embed = discord.Embed(
            title=f"No Warnings for {user.display_name}",
            description=f"{user.mention} has no warnings.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

# Clear all warnings command
@bot.tree.command(name="clear_all_warnings", description="Clear all warnings for a user")
async def clear_all_warnings_slash(interaction: discord.Interaction, user: discord.Member):
    user_id = str(user.id)

    # Check if the user has any warnings
    if user_id in warnings and warnings[user_id]:
        # Clear all warnings
        warnings[user_id] = []
        save_warnings(warnings)
        
        # Send success message in an embed
        embed = discord.Embed(
            title="All Warnings Cleared",
            description=f"All warnings for {user.mention} have been cleared.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Action taken by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)
    else:
        # Send message if no warnings exist
        embed = discord.Embed(
            title="No Warnings Found",
            description=f"{user.mention} has no warnings to clear.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

# ping slash command

@tree.command(name="ping", description="Check bot's latency")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # in ms
    now = datetime.now(timezone.utc)
    uptime_duration = now - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

    embed = discord.Embed(
        title="SWAT Roleplay Community",
        description=(
            "Information about the bot status\n"
            f"> 🏓 Latency: `{latency} ms`\n"
            f"> ⏱️ Uptime: `{uptime_str}`"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    await interaction.response.send_message(embed=embed)



# say slash command

@tree.command(name="say", description="Make the bot say something")

async def say_slash(interaction: discord.Interaction, message: str):

    await interaction.response.send_message(message)


# slowmode slash command

@tree.command(name="slowmode", description="Set the slowmode duration for a channel")

@commands.has_permissions(manage_channels=True)

async def slowmode_slash(interaction: discord.Interaction, seconds: int):

    await interaction.channel.edit(slowmode_delay=seconds)

    embed = discord.Embed(description=f"Slowmode has been set to {seconds} seconds.", color=discord.Color.green())

    await interaction.response.send_message(embed=embed)

# uptime slash command

@tree.command(name="up_time", description="Show how long the bot has been running.")
async def uptime_slash(interaction: discord.Interaction):
    # Calculate uptime
    now = discord.utils.utcnow()
    uptime_seconds = int((now - bot.start_time).total_seconds())

    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Pluralization helper
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
        title="🕒 Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Thanks for keeping me running!")

    await interaction.response.send_message(embed=embed)

# embed slash command

@tree.command(name="embed", description="Make an advanced embed")
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
    try:
        embed_color = discord.Color(int(color.lstrip("#"), 16))
    except ValueError:
        await interaction.response.send_message("Invalid color! Please use a hex color code like `#3498db`.", ephemeral=True)
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

# afk slash command

@tree.command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Optional reason for going AFK")
async def afk_slash(interaction: discord.Interaction, reason: str = "AFK"):

    afk_role = discord.utils.get(interaction.guild.roles, name="AFK")

    if not afk_role:
        afk_role = await interaction.guild.create_role(name="AFK", reason="AFK system initialization")

        for channel in interaction.guild.channels:
            try:
                await channel.set_permissions(afk_role, speak=False, send_messages=False)
            except Exception:
                continue  # Skip if perms can't be set (like threads or restricted categories)

    if afk_role in interaction.user.roles:
        await interaction.response.send_message("You're already marked as AFK.", ephemeral=True)
        return

    await interaction.user.add_roles(afk_role, reason=reason)

    embed = discord.Embed(
        description=f"{interaction.user.mention} is now AFK: {reason}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    await interaction.response.send_message(embed=embed)

# unafk slash command

@tree.command(name="unafk", description="Remove yourself from AFK")
async def unafk_slash(interaction: discord.Interaction):
    afk_role = discord.utils.get(interaction.guild.roles, name="AFK")

    if not afk_role or afk_role not in interaction.user.roles:
        await interaction.response.send_message("You're not currently marked as AFK.", ephemeral=True)
        return

    await interaction.user.remove_roles(afk_role)

    embed = discord.Embed(
        description=f"{interaction.user.mention} is no longer AFK",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )

    await interaction.response.send_message(embed=embed)

# serverinfo slash command

@tree.command(name="server_info", description="Get information about the server")
async def serverinfo_slash(interaction: discord.Interaction):
    guild = interaction.guild

    # Check if the owner is available
    owner = guild.owner if guild.owner else "Owner not found"
    owner_mention = owner.mention if guild.owner else owner  # If owner is available, mention them

    # Create the embed
    embed = discord.Embed(
        title=f"Server Info for {guild.name}",
        color=discord.Color.green()
    )

    # Add fields to the embed
    embed.add_field(name="Server Name", value=guild.name)
    embed.add_field(name="Server ID", value=guild.id)
    embed.add_field(name="Owner", value=owner_mention)  # Mention the owner if available
    embed.add_field(name="Member Count", value=guild.member_count)
    embed.add_field(name="Channel Count", value=len(guild.channels))
    embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"))

    # Handle the server icon (if available)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    else:
        embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")  # Default avatar image if no icon

    # Send the message with the embed
    await interaction.response.send_message(embed=embed)






# userinfo slash command

@tree.command(name="user_info", description="Get information about a user.")
async def userinfo_slash(interaction: discord.Interaction, member: discord.Member):
    roles = [role.mention for role in member.roles if role != member.guild.default_role]
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

    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

    await interaction.response.send_message(embed=embed)

# roleinfo slash command

@tree.command(name="roleinfo", description="Get information about a specific role")

async def roleinfo_slash(interaction: discord.Interaction, role: discord.Role):

    embed = discord.Embed(title=f"Role Info for {role.name}", color=role.color)

    embed.add_field(name="Role Name", value=role.name, inline=False)

    embed.add_field(name="Created At", value=role.created_at.strftime("%B %d, %Y"), inline=False)

    embed.add_field(name="Position", value=role.position, inline=False)

    embed.add_field(name="Permissions", value=", ".join([perm[0] for perm in role.permissions if perm[1]]), inline=False)

    await interaction.response.send_message(embed=embed)

# invite slash command for the server

@tree.command(name="invite", description="Get the server's invite link")

async def server_invite_slash(interaction: discord.Interaction):

    # Get the first invite in the server (if it exists)

    invites = await interaction.guild.invites()

    if invites:

        invite = invites[0]  # Get the first invite

        embed = discord.Embed(title="Server Invite Link", description=f"this is the server invite {invite.url} to join the server.", color=discord.Color.green())

    else:

        embed = discord.Embed(title="Server Invite Link", description="No invites available. Please try again later.", color=discord.Color.red())

    await interaction.response.send_message(embed=embed)

# nickname slash command

@tree.command(name="nickname", description="Change a user's nickname")

async def nickname_slash(interaction: discord.Interaction, user: discord.User, new_nickname: str):

    await user.edit(nick=new_nickname)

    embed = discord.Embed(description=f"{user}'s nickname has been changed to {new_nickname}.", color=discord.Color.green())

    await interaction.response.send_message(embed=embed)

# servericon slash command

@tree.command(name="servericon", description="Display the server's icon")

async def servericon_slash(interaction: discord.Interaction):

    embed = discord.Embed(title=f"{interaction.guild.name} Server Icon", color=discord.Color.blue())

    embed.set_image(url=interaction.guild.icon.url)

    await interaction.response.send_message(embed=embed)

# remindme slash command

@tree.command(name="remindme", description="Set a reminder")

async def remindme_slash(interaction: discord.Interaction, time: int, reminder: str):

    await interaction.response.send_message(f"⏰ Reminder set for {time} seconds: {reminder}", ephemeral=True)

    await asyncio.sleep(time)

    await interaction.channel.send(f"🔔 Reminder: {reminder}")























# Slash command to send last 20 lines from error.log
@bot.tree.command(name="error_logs", description="View the latest error logs from the bot.")
async def error_logs(interaction: discord.Interaction):
    file_path = "error.log"  # Your log file name

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        await interaction.response.send_message("⚠️ `error.log` not found.", ephemeral=True)
        return

    last_lines = lines[-20:] if len(lines) > 20 else lines
    log_text = "".join(last_lines)

    if len(log_text) > 4000:
        log_text = log_text[-4000:]  # Truncate to fit in embed

    embed = discord.Embed(
        title="🧾 Latest Error Logs",
        description=f"```log\n{log_text}\n```",
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)















# IDs and constants
STAFF_ROLE_ID = 1343234687505530902
LOA_ROLE_ID = 1343299322804043900
SUSPENDED_INFRACTION_TYPE = "suspended"

SHIFT_ROLE_ID = 1343299303459913761
BREAK_ROLE_ID = 1343299319939207208
SHIFT_LOG_CHANNEL_ID = 1381409066156425236

INFRACTION_FILE = "infractions.json"
SHIFT_DATA_FILE = "shift_data.json"

# Helper embeds
def create_embed(title, description, color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)

# Load/Save infractions
def load_infractions():
    try:
        with open(INFRACTION_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_infractions(data):
    with open(INFRACTION_FILE, "w") as f:
        json.dump(data, f, indent=4)

infractions = load_infractions()

# Load/Save shift data
def load_shift_data():
    try:
        with open(SHIFT_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Structure: {user_id: {"total_shift": seconds, "total_break": seconds, "current_shift_start": timestamp or None, "current_break_start": timestamp or None, "shift_type": str or None}}
        return {}

def save_shift_data(data):
    with open(SHIFT_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

shift_data = load_shift_data()

# Check if user has staff role
def is_staff(member: discord.Member):
    return any(role.id == STAFF_ROLE_ID for role in member.roles)

# Check if user has loa role
def has_loa_role(member: discord.Member):
    return any(role.id == LOA_ROLE_ID for role in member.roles)

# Check if user is suspended by infraction
def is_suspended(user_id: str):
    user_infractions = infractions.get(user_id, [])
    for inf in user_infractions:
        if inf.get("type") == SUSPENDED_INFRACTION_TYPE:
            return True
    return False

# --- INFRACTION COMMANDS ---

@bot.tree.command(name="infraction_add", description="Add an infraction to a user")
@app_commands.describe(user="User to add infraction to", reason="Reason for the infraction", infraction_type="Type of infraction (optional)")
async def infraction_add(interaction: discord.Interaction, user: discord.Member, reason: str, infraction_type: str = "general"):
    if not is_staff(interaction.user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "You must be staff to add infractions.", discord.Color.red()), ephemeral=True)
        return

    user_id = str(user.id)
    entry = {
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": infraction_type.lower()
    }
    infractions.setdefault(user_id, []).append(entry)
    save_infractions(infractions)

    await interaction.response.send_message(embed=create_embed(
        "Infraction Added",
        f"Infraction added to {user.mention}\nReason: {reason}\nType: {infraction_type}"
    ))

    # If suspended infraction added, forcibly end shift & break
    if infraction_type.lower() == SUSPENDED_INFRACTION_TYPE:
        if user_id in shift_data:
            shift_user = shift_data[user_id]
            if shift_user.get("current_shift_start"):
                # End shift forcibly
                shift_start_ts = shift_user["current_shift_start"]
                shift_end_ts = datetime.now(timezone.utc).timestamp()
                worked = shift_end_ts - shift_start_ts
                shift_user["total_shift"] = shift_user.get("total_shift", 0) + worked
                shift_user["current_shift_start"] = None
                shift_user["shift_type"] = None
            if shift_user.get("current_break_start"):
                break_start_ts = shift_user["current_break_start"]
                break_end_ts = datetime.now(timezone.utc).timestamp()
                brk = break_end_ts - break_start_ts
                shift_user["total_break"] = shift_user.get("total_break", 0) + brk
                shift_user["current_break_start"] = None
            save_shift_data(shift_data)

            # Remove roles if possible
            member = interaction.guild.get_member(int(user_id))
            if member:
                try:
                    await member.remove_roles(interaction.guild.get_role(SHIFT_ROLE_ID), interaction.guild.get_role(BREAK_ROLE_ID))
                except:
                    pass

@bot.tree.command(name="infraction_view", description="View infractions for a user")
@app_commands.describe(user="User to view infractions for")
async def infraction_view(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "You must be staff to view infractions.", discord.Color.red()), ephemeral=True)
        return

    user_id = str(user.id)
    user_infractions = infractions.get(user_id, [])
    if not user_infractions:
        await interaction.response.send_message(embed=create_embed(f"No Infractions", f"{user.mention} has no infractions.", discord.Color.green()))
        return

    embed = discord.Embed(title=f"Infractions for {user}", color=discord.Color.orange())
    for i, inf in enumerate(user_infractions, start=1):
        ts = inf.get("timestamp")
        reason = inf.get("reason")
        typ = inf.get("type", "general")
        embed.add_field(name=f"#{i} [{typ}]", value=f"**Reason:** {reason}\n**Time:** {ts}", inline=False)

    await interaction.response.send_message(embed=embed)

# --- SHIFT COMMANDS ---

# Helper to format seconds to hh:mm:ss
def format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"

@bot.tree.command(name="shift_start", description="Start your shift with a shift type")
@app_commands.describe(shift_type="Type of shift (e.g. day, night)")
async def shift_start(interaction: discord.Interaction, shift_type: str):
    user = interaction.user
    user_id = str(user.id)

    if not is_staff(user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can start shifts.", discord.Color.red()), ephemeral=True)
        return

    if has_loa_role(user):
        await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot start a shift.", discord.Color.red()), ephemeral=True)
        return

    if is_suspended(user_id):
        await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot start a shift.", discord.Color.red()), ephemeral=True)
        return

    user_shift = shift_data.setdefault(user_id, {
        "total_shift": 0,
        "total_break": 0,
        "current_shift_start": None,
        "current_break_start": None,
        "shift_type": None
    })

    if user_shift["current_shift_start"]:
        await interaction.response.send_message(embed=create_embed("Shift Already Started", "You are already on shift.", discord.Color.red()), ephemeral=True)
        return

    if user_shift["current_break_start"]:
        await interaction.response.send_message(embed=create_embed("On Break", "You cannot start a new shift while on a break. End your break first.", discord.Color.red()), ephemeral=True)
        return

    # Start shift
    user_shift["current_shift_start"] = datetime.now(timezone.utc).timestamp()
    user_shift["shift_type"] = shift_type.lower()
    save_shift_data(shift_data)

    # Add shift role
    guild = interaction.guild
    shift_role = guild.get_role(SHIFT_ROLE_ID)
    break_role = guild.get_role(BREAK_ROLE_ID)
    member = guild.get_member(user.id)

    # Remove break role if any
    if break_role in member.roles:
        await member.remove_roles(break_role)

    # Add shift role if missing
    if shift_role not in member.roles:
        await member.add_roles(shift_role)

    # Log to channel
    log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
    if log_chan:
        embed = create_embed(
            "Shift Started",
            f"{user.mention} started a **{shift_type}** shift.",
            discord.Color.green()
        )
        await log_chan.send(embed=embed)

    await interaction.response.send_message(embed=create_embed("Shift Started", f"Your **{shift_type}** shift has started."), ephemeral=True)

@bot.tree.command(name="shift_end", description="End your current shift")
async def shift_end(interaction: discord.Interaction):
    user = interaction.user
    user_id = str(user.id)

    if not is_staff(user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can end shifts.", discord.Color.red()), ephemeral=True)
        return

    user_shift = shift_data.get(user_id)
    if not user_shift or not user_shift.get("current_shift_start"):
        await interaction.response.send_message(embed=create_embed("No Shift", "You are not currently on shift.", discord.Color.red()), ephemeral=True)
        return

    # End shift time calculation
    shift_start_ts = user_shift["current_shift_start"]
    shift_end_ts = datetime.now(timezone.utc).timestamp()
    worked = shift_end_ts - shift_start_ts
    user_shift["total_shift"] = user_shift.get("total_shift", 0) + worked
    user_shift["current_shift_start"] = None
    shift_type = user_shift.get("shift_type")
    user_shift["shift_type"] = None
    save_shift_data(shift_data)

    # Remove shift and break roles
    guild = interaction.guild
    shift_role = guild.get_role(SHIFT_ROLE_ID)
    break_role = guild.get_role(BREAK_ROLE_ID)
    member = guild.get_member(user.id)

    roles_to_remove = []
    if shift_role in member.roles:
        roles_to_remove.append(shift_role)
    if break_role in member.roles:
        roles_to_remove.append(break_role)
    if roles_to_remove:
        await member.remove_roles(*roles_to_remove)

    # Log
    log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
    if log_chan:
        embed = create_embed(
            "Shift Ended",
            f"{user.mention} ended their shift.\nShift Type: **{shift_type or 'Unknown'}**\nDuration: {format_seconds(worked)}",
            discord.Color.orange()
        )
        await log_chan.send(embed=embed)

    await interaction.response.send_message(embed=create_embed("Shift Ended", f"Your shift has ended. Duration: {format_seconds(worked)}"), ephemeral=True)

@bot.tree.command(name="break_start", description="Start your break")
async def break_start(interaction: discord.Interaction):
    user = interaction.user
    user_id = str(user.id)

    if not is_staff(user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can start breaks.", discord.Color.red()), ephemeral=True)
        return

    if has_loa_role(user):
        await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot start a break.", discord.Color.red()), ephemeral=True)
        return

    if is_suspended(user_id):
        await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot start a break.", discord.Color.red()), ephemeral=True)
        return

    user_shift = shift_data.get(user_id)
    if not user_shift or not user_shift.get("current_shift_start"):
        await interaction.response.send_message(embed=create_embed("Not On Shift", "You must be on shift to start a break.", discord.Color.red()), ephemeral=True)
        return

    if user_shift.get("current_break_start"):
        await interaction.response.send_message(embed=create_embed("Already On Break", "You are already on a break.", discord.Color.red()), ephemeral=True)
        return

    # Start break
    user_shift["current_break_start"] = datetime.now(timezone.utc).timestamp()
    save_shift_data(shift_data)

    # Remove shift role, add break role
    guild = interaction.guild
    shift_role = guild.get_role(SHIFT_ROLE_ID)
    break_role = guild.get_role(BREAK_ROLE_ID)
    member = guild.get_member(user.id)

    if shift_role in member.roles:
        await member.remove_roles(shift_role)
    if break_role not in member.roles:
        await member.add_roles(break_role)

    # Log
    log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
    if log_chan:
        embed = create_embed(
            "Break Started",
            f"{user.mention} started a break.",
            discord.Color.gold()
        )
        await log_chan.send(embed=embed)

    await interaction.response.send_message(embed=create_embed("Break Started", "You have started your break."), ephemeral=True)

@bot.tree.command(name="break_end", description="End your break and return to shift")
async def break_end(interaction: discord.Interaction):
    user = interaction.user
    user_id = str(user.id)

    if not is_staff(user):
        await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can end breaks.", discord.Color.red()), ephemeral=True)
        return

    if has_loa_role(user):
        await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot end a break.", discord.Color.red()), ephemeral=True)
        return

    if is_suspended(user_id):
        await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot end a break.", discord.Color.red()), ephemeral=True)
        return

    user_shift = shift_data.get(user_id)
    if not user_shift or not user_shift.get("current_break_start"):
        await interaction.response.send_message(embed=create_embed("Not On Break", "You are not currently on a break.", discord.Color.red()), ephemeral=True)
        return

    # Calculate break time
    break_start_ts = user_shift["current_break_start"]
    break_end_ts = datetime.now(timezone.utc).timestamp()
    brk = break_end_ts - break_start_ts
    user_shift["total_break"] = user_shift.get("total_break", 0) + brk
    user_shift["current_break_start"] = None
    save_shift_data(shift_data)

    # Remove break role, add shift role
    guild = interaction.guild
    shift_role = guild.get_role(SHIFT_ROLE_ID)
    break_role = guild.get_role(BREAK_ROLE_ID)
    member = guild.get_member(user.id)

    if break_role in member.roles:
        await member.remove_roles(break_role)
    if shift_role not in member.roles:
        await member.add_roles(shift_role)

    # Log
    log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
    if log_chan:
        embed = create_embed(
            "Break Ended",
            f"{user.mention} ended their break.",
            discord.Color.green()
        )
        await log_chan.send(embed=embed)

    await interaction.response.send_message(embed=create_embed("Break Ended", f"Your break has ended after {format_seconds(brk)}."), ephemeral=True)

# --- LEADERBOARD COMMAND ---

@bot.tree.command(name="shift_leaderboard", description="View leaderboard for total shift and break times")
async def shift_leaderboard(interaction: discord.Interaction):
    # Build leaderboard sorted by total_shift descending
    if not shift_data:
        await interaction.response.send_message(embed=create_embed("No Data", "No shift data available.", discord.Color.red()), ephemeral=True)
        return

    # Prepare data
    leaderboard = []
    for uid, data in shift_data.items():
        total_shift = data.get("total_shift", 0)
        total_break = data.get("total_break", 0)
        leaderboard.append((uid, total_shift, total_break))
    leaderboard.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="Shift Leaderboard", color=discord.Color.purple())

    top = leaderboard[:10]
    for rank, (uid, shift_sec, break_sec) in enumerate(top, start=1):
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"User ID {uid}"
        embed.add_field(
            name=f"{rank}. {name}",
            value=f"Shift Time: {format_seconds(shift_sec)}\nBreak Time: {format_seconds(break_sec)}",
            inline=False,
        )

    await interaction.response.send_message(embed=embed)































# Create the /suggestion command
@bot.tree.command(name="suggestion", description="Submit a suggestion for the bot or server.")
async def suggestion_slash(interaction: discord.Interaction, suggestion: str):
    # Check if the suggestion is empty or too short
    if not suggestion or len(suggestion) < 10:
        await interaction.response.send_message("Please provide a valid suggestion (at least 10 characters long).", ephemeral=True)
        return
    
    # Define the suggestion log channel (change to your desired channel ID)
    suggestion_channel_id = 1343622169086918758  # Replace with your suggestion channel ID
    suggestion_channel = interaction.guild.get_channel(suggestion_channel_id)
    
    # Create an embed to display the suggestion
    embed = discord.Embed(
        title="New Suggestion",
        description=suggestion,
        color=discord.Color.green()
    )
    embed.add_field(name="Submitted by", value=f"{interaction.user}", inline=True)
    embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
    embed.set_footer(text="SWAT Roleplay Community")

    # Send the suggestion to the suggestion channel
    await suggestion_channel.send(embed=embed)

    # Acknowledge the user
    await interaction.response.send_message("Thank you for your suggestion! It has been submitted for review.", ephemeral=True)

## Slash command for staff suggestions
@bot.tree.command(name="staff_suggestion", description="Submit a staff suggestion for the bot or server.")
@app_commands.checks.has_role(1343234687505530902)  # Replace with your actual staff role ID
async def staff_suggestion_slash(interaction: discord.Interaction, staff_suggestion: str):
    if len(staff_suggestion.strip()) < 10:
        await interaction.response.send_message(
            "Please provide a valid suggestion (at least 10 characters long).",
            ephemeral=True
        )
        return

    suggestion_channel_id = 1373704702977376297  # Replace with your suggestion channel ID
    suggestion_channel = interaction.guild.get_channel(suggestion_channel_id)

    if not suggestion_channel:
        await interaction.response.send_message(
            "Suggestion channel not found. Please contact an admin.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="New Staff Suggestion",
        description=staff_suggestion,
        color=discord.Color.green()
    )
    embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
    embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
    embed.set_footer(text="SWAT Roleplay Community")

    await suggestion_channel.send(embed=embed)

    await interaction.response.send_message(
        "Thank you for your suggestion! It has been submitted for review.",
        ephemeral=True
    )

# Error handler for missing role
@staff_suggestion_slash.error
async def staff_suggestion_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True
        )


# Create the /staff_feedback command
@bot.tree.command(name="staff_feedback", description="Submit feedback for a staff member.")
async def staff_feedback_slash(interaction: discord.Interaction, text: str, staff: discord.Member):
    # Define the required role ID for the staff member (the role they must have)
    required_role_id = 1343234687505530902  # Replace with your staff role ID

    # Prevent users from giving feedback to themselves
    if interaction.user == staff:
        await interaction.response.send_message("You cannot give feedback to yourself.", ephemeral=True)
        return

    # Check if the mentioned staff member has the required role
    if required_role_id not in [role.id for role in staff.roles]:
        await interaction.response.send_message(f"{staff.mention} does not have the required staff role.", ephemeral=True)
        return

    # Check if the feedback text is empty or too short
    if not text or len(text) < 10:
        await interaction.response.send_message("Please provide valid feedback (at least 10 characters long).", ephemeral=True)
        return
    
    # Define the feedback log channel (replace with your feedback channel ID)
    feedback_channel_id = 1343621982549311519  # The feedback channel ID
    feedback_channel = interaction.guild.get_channel(feedback_channel_id)

    # Create an embed to display the feedback
    embed = discord.Embed(
        title="Staff Feedback",
        description=text,
        color=discord.Color.blue()
    )
    embed.add_field(name="Feedback for", value=f"{staff.mention}", inline=True)
    embed.add_field(name="Submitted by", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=True)
    embed.set_footer(text="SWAT Roleplay Community")

    # Send the feedback to the feedback channel
    await feedback_channel.send(f"-# <:PING:1381073968873607229> {staff.mention}", embed=embed)

    # Acknowledge the user
    await interaction.response.send_message(f"Thank you for your feedback about {staff.mention}. It has been submitted for review.", ephemeral=True)


# List to hold events in memory, will be saved in a JSON file
events = []

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
        json.dump(events, file)

# Command to create an event
@bot.tree.command(name="event", description="Create an event")
async def event_slash(interaction: discord.Interaction, event_name: str, event_date: str, event_time: str, event_description: str):
    # Combine date and time into a single datetime object
    try:
        event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M %H:%M")
    except ValueError:
        await interaction.response.send_message("Invalid date/time format. Please use 'YYYY-MM-DD' for the date and 'HH:MM' for the time.", ephemeral=True)
        return

    # Save the event data
    event_data = {
        "name": event_name,
        "date": event_datetime.strftime("%Y-%m-%d"),
        "time": event_datetime.strftime("%H:%M"),
        "description": event_description,
        "creator": interaction.user.name
    }
    events.append(event_data)

    # Save events to the file
    save_events()

    # Respond to the user
    embed = discord.Embed(
        title=f"Event Created: {event_name}",
        description=f"**Date:** {event_datetime.strftime('%Y-%m-%d')}\n"
                    f"**Time:** {event_datetime.strftime('%H:%M')}\n"
                    f"**Description:** {event_description}\n"
                    f"**Creator:** {interaction.user.name}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Command to view all upcoming events
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
            value=f"**Date:** {event['date']}\n"
                  f"**Time:** {event['time']}\n"
                  f"**Description:** {event['description']}\n"
                  f"**Creator:** {event['creator']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# Load events when the bot starts
load_events()

































































STAFF_ROLE_ID = 1375985192174354442

warnings_db = {}

class ModPanelView(discord.ui.View):
    def __init__(self, target: discord.Member):
        super().__init__(timeout=None)
        self.target = target

    # Buttons

    @discord.ui.button(label="⚠ Warn", style=discord.ButtonStyle.danger)
    async def warn(self, interaction: discord.Interaction, button: discord.ui.Button):
        warnings_db[self.target.id] = warnings_db.get(self.target.id, 0) + 1
        try:
            await self.target.send(f"You have been warned in **{interaction.guild.name}**. Total warnings: {warnings_db[self.target.id]}")
        except discord.Forbidden:
            # Can't DM user, just ignore
            pass
        await interaction.response.send_message(
            f"⚠️ {self.target.mention} warned. Total warnings: `{warnings_db[self.target.id]}`", ephemeral=False
        )

    @discord.ui.button(label="👢 Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target.kick(reason=f"Kicked by {interaction.user}")
            await interaction.response.send_message(f"👢 {self.target.mention} has been kicked.", ephemeral=False)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I can't kick this user.", ephemeral=True)

    @discord.ui.button(label="❌ Close Panel", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    # Dropdown for more actions

    @discord.ui.select(
        placeholder="More actions...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="View Warnings", description="See how many warnings the user has", emoji="📄"),
            discord.SelectOption(label="Clear Warnings", description="Remove all warnings from the user", emoji="🧹"),
            discord.SelectOption(label="Timeout (10 min)", description="Put the user in timeout for 10 minutes", emoji="🔇"),
        ],
        row=1,
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]

        if choice == "View Warnings":
            count = warnings_db.get(self.target.id, 0)
            await interaction.response.send_message(f"🔍 {self.target.mention} has `{count}` warning(s).", ephemeral=True)

        elif choice == "Clear Warnings":
            if self.target.id in warnings_db:
                del warnings_db[self.target.id]
                try:
                    await self.target.send(f"Your warnings have been cleared in **{interaction.guild.name}**.")
                except discord.Forbidden:
                    pass
                await interaction.response.send_message(f"✅ Cleared all warnings for {self.target.mention}.", ephemeral=False)
            else:
                await interaction.response.send_message("🫧 No warnings to clear.", ephemeral=True)

        elif choice == "Timeout (10 min)":
            try:
                await self.target.timeout(timedelta(minutes=10), reason=f"Timeout by {interaction.user}")
                await interaction.response.send_message(f"🔇 {self.target.mention} has been timed out for 10 minutes.", ephemeral=False)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I can't timeout this user.", ephemeral=True)

@bot.tree.command(name="mod_panel", description="Open a moderation panel.")
@app_commands.describe(user="The user to moderate.")
@app_commands.checks.has_role(STAFF_ROLE_ID)
async def mod_panel(interaction: discord.Interaction, user: discord.Member):
    if user == interaction.user:
        await interaction.response.send_message("❌ You can't moderate yourself.", ephemeral=True)
        return
    if user.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ That user has a higher or equal role than you.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🛠 Moderation Panel",
        description=f"Choose an action for {user.mention}",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Username", value=str(user), inline=True)
    embed.add_field(name="User ID", value=str(user.id), inline=True)
    embed.add_field(name="Warnings", value=str(warnings_db.get(user.id, 0)), inline=True)
    embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

    view = ModPanelView(user)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@mod_panel.error
async def mod_panel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=True)











































# --- Config ---

PROFANITY_LIST = {'badword1', 'badword2', 'badword3'}

TRUSTED_DOMAINS = {'trustedwebsite.com', 'anothertrusted.com'}

WHITELISTED_ROLES = {'VIP'}  # Can be role names or IDs as strings
WHITELISTED_CHANNELS = {'staff-chat'}  # Can be channel names or IDs as strings

# --- State for spam detection ---

MESSAGE_HISTORY = defaultdict(list)
ATTACHMENT_HISTORY = defaultdict(list)
MENTION_HISTORY = defaultdict(list)

# --- Helper functions ---

def contains_profanity(message_content: str) -> bool:
    content = message_content.lower()
    return any(word in content for word in PROFANITY_LIST)

def contains_untrusted_link(message_content: str) -> bool:
    url_pattern = re.compile(r'https?://[^\s]+')
    links = url_pattern.findall(message_content)

    if not links:
        return False

    for link in links:
        if any(domain in link for domain in TRUSTED_DOMAINS):
            continue  # Trusted link
        return True  # Found untrusted link

    return False

def is_overly_capitalized(message_content: str) -> bool:
    if len(message_content) <= 10:
        return False
    upper_count = sum(1 for c in message_content if c.isupper())
    percentage_upper = (upper_count / len(message_content)) * 100
    return percentage_upper > 80

# --- Main message event ---

@bot.event
async def on_message(message: discord.Message):
    # Ignore bot messages
    if message.author.bot:
        return

    # Ignore whitelisted channels
    if (
        (message.channel.name in WHITELISTED_CHANNELS) or
        (str(message.channel.id) in WHITELISTED_CHANNELS)
    ):
        return

    member = message.author
    # Ignore users with whitelisted roles
    if (
        hasattr(message, "guild") and message.guild and isinstance(member, discord.Member)
        and any(
            (role.name in WHITELISTED_ROLES or str(role.id) in WHITELISTED_ROLES)
            for role in member.roles
        )
    ):
        return

    content = message.content

    # Profanity check
    if contains_profanity(content):
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, your message was deleted due to inappropriate content.",
            delete_after=10
        )
        return

    # Untrusted link check
    if contains_untrusted_link(content):
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, links are not allowed in this channel.",
            delete_after=10
        )
        return

    # Over-capitalization check
    if is_overly_capitalized(content):
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, your message was deleted because it is overly capitalized.",
            delete_after=10
        )
        return

    current_time = message.created_at.timestamp()
    user_id = message.author.id

    # Attachment spam check
    if message.attachments:
        ATTACHMENT_HISTORY[user_id].append(current_time)
    # Keep timestamps within the last 5 seconds
    ATTACHMENT_HISTORY[user_id] = [t for t in ATTACHMENT_HISTORY[user_id] if current_time - t < 5]
    if len(ATTACHMENT_HISTORY[user_id]) > 5:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, you are spamming attachments and your message was deleted.",
            delete_after=10
        )
        return

    # Mention spam check
    mention_count = len(message.mentions)
    if mention_count > 3:
        MENTION_HISTORY[user_id].append(current_time)
    MENTION_HISTORY[user_id] = [t for t in MENTION_HISTORY[user_id] if current_time - t < 4]
    if len(MENTION_HISTORY[user_id]) > 3:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, you are spamming mentions and your message was deleted.",
            delete_after=10
        )
        return

    # Message spam check
    MESSAGE_HISTORY[user_id].append(current_time)
    MESSAGE_HISTORY[user_id] = [t for t in MESSAGE_HISTORY[user_id] if current_time - t < 5]
    if len(MESSAGE_HISTORY[user_id]) > 3:
        await message.delete()
        await message.channel.send(
            f"{message.author.mention}, you are spamming and your message was deleted.",
            delete_after=10
        )
        return

    # Process commands if any
    await bot.process_commands(message)




































































SESSION_VOTE_PING_ROLE_ID = 1375985192174354442
SESSION_ROLE_ID = 1375985192174354442
TARGET_CHANNEL_ID = 1373707060977340456
REQUIRED_VOTES = 2
JOIN_LINK = "https://policeroleplay.community/join?code=SWATxRP&placeId=2534724415"

current_votes = set()
session_state = "idle"

class SessionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.message = None
        self.vote_button = discord.ui.Button(label="Vote", style=discord.ButtonStyle.primary)
        self.vote_button.callback = self.vote_callback

        self.start_button = discord.ui.Button(label="Start Session", style=discord.ButtonStyle.success)
        self.start_button.callback = self.start_session

        self.shutdown_button = discord.ui.Button(label="Shutdown Session", style=discord.ButtonStyle.danger)
        self.shutdown_button.callback = self.shutdown_session

        self.low_button = discord.ui.Button(label="Low Session", style=discord.ButtonStyle.secondary)
        self.low_button.callback = self.set_low_session

        self.full_button = discord.ui.Button(label="Full Session", style=discord.ButtonStyle.secondary)
        self.full_button.callback = self.set_full_session

        self.start_vote_button = discord.ui.Button(label="Start Vote", style=discord.ButtonStyle.primary)
        self.start_vote_button.callback = self.reset_vote

        self.reset_buttons_to_vote()

    def reset_buttons_to_vote(self):
        self.clear_items()
        self.add_item(self.vote_button)
        self.add_item(self.start_button)
        self.add_item(self.shutdown_button)

    def set_buttons_to_session(self):
        self.clear_items()
        self.add_item(self.low_button)
        self.add_item(self.full_button)
        self.add_item(self.shutdown_button)

    def set_buttons_to_idle(self):
        self.clear_items()
        self.add_item(self.start_vote_button)
        self.add_item(self.start_button)

    async def vote_callback(self, interaction: discord.Interaction):
        member = interaction.user
        if member.id in current_votes:
            current_votes.remove(member.id)
        else:
            current_votes.add(member.id)

        vote_count = len(current_votes)
        embed = discord.Embed(title="Session Voting", description=f"**{vote_count} of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        await self.message.edit(embed=embed, view=self)

        if vote_count >= REQUIRED_VOTES:
            self.remove_item(self.vote_button)
            embed.description = "✅ **Vote complete. Ready to start the session.**"
            await self.message.edit(embed=embed, view=self)

            for user_id in current_votes:
                user = await bot.fetch_user(user_id)
                try:
                    join_view = discord.ui.View()
                    join_view.add_item(discord.ui.Button(label="Join", url=JOIN_LINK))
                    dm_embed = discord.Embed(title="Session Invite", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())
                    await user.send(embed=dm_embed, view=join_view)
                except:
                    print(f"Could not DM {user_id}")

        await interaction.response.defer()

    async def start_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to start a session.", ephemeral=True)

        self.set_buttons_to_session()
        global session_state
        session_state = "idle"

        embed = discord.Embed(title="Session Started", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())
        
        # Adding all 4 buttons (Join, Low Session, Full Session, Shutdown Session)
        join_button = discord.ui.Button(label="Join", url=JOIN_LINK)
        view = discord.ui.View().add_item(join_button)
        view.add_item(self.low_button)
        view.add_item(self.full_button)
        view.add_item(self.shutdown_button)
        
        await self.message.edit(embed=embed, view=view)
        await interaction.response.defer()

        # Notify users via DM with the Join button
        for user_id in current_votes:
            user = await bot.fetch_user(user_id)
            try:
                join_view = discord.ui.View()
                join_view.add_item(discord.ui.Button(label="Join", url=JOIN_LINK))
                dm_embed = discord.Embed(title="Session Invite", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())
                await user.send(embed=dm_embed, view=join_view)
            except:
                print(f"Could not DM {user_id}")

    async def set_low_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission.", ephemeral=True)

        global session_state
        session_state = "low"
        embed = discord.Embed(title="Low Session Active", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.orange())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def set_full_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission.", ephemeral=True)

        global session_state
        session_state = "full"
        embed = discord.Embed(title="Full Session Active", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.red())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def shutdown_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to shut down the session.", ephemeral=True)

        self.set_buttons_to_idle()
        global current_votes, session_state
        current_votes.clear()
        session_state = "idle"
        embed = discord.Embed(title="⚠️ Session Shut Down", color=discord.Color.dark_red())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def reset_vote(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to start a vote.", ephemeral=True)

        self.reset_buttons_to_vote()
        global current_votes
        current_votes.clear()
        embed = discord.Embed(title="Session Voting", description=f"**0 of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        await self.message.edit(content=f"<@&{SESSION_ROLE_ID}>", embed=embed, view=self)
        await interaction.response.defer()

    def _has_session_role(self, member: discord.Member):
        return any(role.id == SESSION_ROLE_ID for role in member.roles)

class SessionCommands(app_commands.Group):
    @app_commands.command(name="vote", description="Start a session vote")
    async def vote(self, interaction: discord.Interaction):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("You can only start the vote in the designated session channel.", ephemeral=True)

        view = SessionView()
        embed = discord.Embed(title="Session Voting", description=f"**0 of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        msg = await interaction.channel.send(content=f"<@&{TARGET_CHANNEL_ID}>", embed=embed, view=view)
        view.message = msg
        await interaction.response.send_message("✅ Session vote started.", ephemeral=True)

tree.add_command(SessionCommands(name="session"))



# Replace with your Discord user ID
OWNER_ID = 1276264248095412387  # <-- Replace this with your actual ID

@bot.tree.command(name="shutdown", description="Shut down the bot (owner only)")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You do not have permission to shut down the bot.", ephemeral=True)
        return

    await interaction.response.send_message("🛑 Shutting down the bot... Goodbye!", ephemeral=True)
    await bot.close()





















































































































MOD_ROLE_ID = 1343234687505530902  # Required role ID to run commands

def create_embed(title, desc, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=desc, color=color)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_mod_role(self, member: discord.Member) -> bool:
        return any(role.id == MOD_ROLE_ID for role in member.roles)

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to kick members.", discord.Color.red()), ephemeral=True)

        await member.kick(reason=reason)
        await interaction.response.send_message(embed=create_embed("User Kicked", f"{member.mention} was kicked.\nReason: {reason}"))

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for banning")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to ban members.", discord.Color.red()), ephemeral=True)

        await member.ban(reason=reason)
        await interaction.response.send_message(embed=create_embed("User Banned", f"{member.mention} was banned.\nReason: {reason}"))

    @app_commands.command(name="mute", description="Mute a user for a set number of minutes")
    @app_commands.describe(member="Member to mute", duration="Duration in minutes")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = 10):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if member.id == 1276264248095412387:  # Protect specific user from mute
            return await interaction.response.send_message(embed=create_embed("Error", "You cannot mute this user.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage roles.", discord.Color.red()), ephemeral=True)

        muted_role = get(interaction.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)

        await member.add_roles(muted_role)
        await interaction.response.send_message(embed=create_embed("User Muted", f"{member.mention} has been muted for {duration} minutes."))

        # Wait asynchronously for duration and unmute
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(minutes=duration))
        await member.remove_roles(muted_role)

    @app_commands.command(name="unmute", description="Unmute a user")
    @app_commands.describe(member="Member to unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage roles.", discord.Color.red()), ephemeral=True)

        muted_role = get(interaction.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(embed=create_embed("User Unmuted", f"{member.mention} has been unmuted."))
        else:
            await interaction.response.send_message(embed=create_embed("Error", f"{member.mention} is not muted.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their ID")
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to unban members.", discord.Color.red()), ephemeral=True)

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(embed=create_embed("User Unbanned", f"{user.mention} has been unbanned."))
        except discord.NotFound:
            await interaction.response.send_message(embed=create_embed("Error", "User not found in ban list.", discord.Color.red()), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=create_embed("Error", "Invalid user ID format.", discord.Color.red()), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=create_embed("Error", f"Something went wrong.\n{e}", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="clear", description="Clear a number of messages in the channel")
    @app_commands.describe(amount="How many messages to delete")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage messages.", discord.Color.red()), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=create_embed("Cleared Messages", f"Deleted {len(deleted)} messages."), ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock the current channel for @everyone")
    async def unlock(self, interaction: discord.Interaction):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage channels.", discord.Color.red()), ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(embed=create_embed("Channel Unlocked", f"{interaction.channel.mention} is now unlocked."))

    @app_commands.command(name="lock", description="Lock the current channel from @everyone")
    async def lock(self, interaction: discord.Interaction):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage channels.", discord.Color.red()), ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(embed=create_embed("Channel Locked", f"{interaction.channel.mention} is now locked."))

    REPORT_CHANNEL_ID = 1358405704393822288  # replace with your actual mod channel ID

    @app_commands.command(name="report", description="Report a user to the moderators")
    @app_commands.describe(user="The user you want to report", reason="The reason for the report")
    async def report(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        embed = discord.Embed(
            title="🚨 New User Report",
            description=f"**Reporter:** {interaction.user.mention}\n**Reported User:** {user.mention}\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"User ID: {user.id} | Reported from: #{interaction.channel.name}")
        embed.timestamp = discord.utils.utcnow()

        # Send report to mod channel
        mod_channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
            await interaction.response.send_message(embed=create_embed("Report Submitted", "Your report has been sent to the moderators. Thank you."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_embed("Error", "Could not find the report channel. Please contact staff.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="poll", description="Create a simple yes/no poll")
    @app_commands.describe(question="The poll question")
    async def poll(self, interaction: discord.Interaction, question: str):
        class PollView(View):
            def __init__(self):
                super().__init__(timeout=None)
                self.yes_votes = 0
                self.no_votes = 0

            @discord.ui.button(label="👍 Yes", style=discord.ButtonStyle.success)
            async def yes_button(self, interaction: discord.Interaction, button: Button):
                self.yes_votes += 1
                await interaction.response.send_message("Vote counted for **Yes**!", ephemeral=True)

            @discord.ui.button(label="👎 No", style=discord.ButtonStyle.danger)
            async def no_button(self, interaction: discord.Interaction, button: Button):
                self.no_votes += 1
                await interaction.response.send_message("Vote counted for **No**!", ephemeral=True)

        embed = create_embed("📊 New Poll", question)
        await interaction.response.send_message(embed=embed, view=PollView())














































































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

class EditTitleModal(discord.ui.Modal, title="Edit Embed Title"):
    title_input = discord.ui.TextInput(label="New Title", max_length=256, required=True)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        embed.title = self.title_input.value
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Embed title updated!", ephemeral=True)

class EditDescriptionModal(discord.ui.Modal, title="Edit Embed Description"):
    description_input = discord.ui.TextInput(label="New Description", style=discord.TextStyle.paragraph, max_length=4000, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        embed.description = self.description_input.value
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Embed description updated!", ephemeral=True)

class EditColorModal(discord.ui.Modal, title="Edit Embed Color"):
    color_input = discord.ui.TextInput(label="Color (Hex or name)", max_length=20, required=False, placeholder="#7289DA or red")

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        color_str = self.color_input.value
        embed.color = parse_color(color_str) if color_str else discord.Color.default()
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Embed color updated!", ephemeral=True)

class EditImageModal(discord.ui.Modal, title="Edit Embed Image URL"):
    image_url_input = discord.ui.TextInput(label="Image URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        url = self.image_url_input.value.strip()
        if url:
            embed.set_image(url=url)
        else:
            embed.set_image(url=None)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Embed image updated!", ephemeral=True)

class EditFooterTextModal(discord.ui.Modal, title="Edit Embed Footer Text"):
    footer_text_input = discord.ui.TextInput(label="Footer Text", max_length=2048, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        footer_icon_url = embed.footer.icon_url if embed.footer else None
        embed.set_footer(text=self.footer_text_input.value, icon_url=footer_icon_url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Footer text updated!", ephemeral=True)

class EditFooterIconModal(discord.ui.Modal, title="Edit Embed Footer Icon URL"):
    footer_icon_input = discord.ui.TextInput(label="Footer Icon URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        footer_text = embed.footer.text if embed.footer else None
        url = self.footer_icon_input.value.strip()
        if url == "":
            url = None
        embed.set_footer(text=footer_text, icon_url=url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Footer icon updated!", ephemeral=True)

class EditAuthorNameModal(discord.ui.Modal, title="Edit Embed Author Name"):
    author_name_input = discord.ui.TextInput(label="Author Name", max_length=256, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        icon_url = embed.author.icon_url if embed.author else None
        embed.set_author(name=self.author_name_input.value or discord.Embed.Empty, icon_url=icon_url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Author name updated!", ephemeral=True)

class EditAuthorIconModal(discord.ui.Modal, title="Edit Embed Author Icon URL"):
    author_icon_input = discord.ui.TextInput(label="Author Icon URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        name = embed.author.name if embed.author else None
        url = self.author_icon_input.value.strip()
        if url == "":
            url = None
        embed.set_author(name=name or discord.Embed.Empty, icon_url=url)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Author icon updated!", ephemeral=True)

class EditThumbnailModal(discord.ui.Modal, title="Edit Embed Thumbnail URL"):
    thumbnail_url_input = discord.ui.TextInput(label="Thumbnail URL", max_length=1024, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else discord.Embed()
        url = self.thumbnail_url_input.value.strip()
        if url:
            embed.set_thumbnail(url=url)
        else:
            embed.set_thumbnail(url=None)
        await self.embed_message.edit(content=self.embed_message.content, embed=embed)
        await interaction.response.send_message("✅ Thumbnail updated!", ephemeral=True)

# --- New modal for message content ---

class EditMessageContentModal(discord.ui.Modal, title="Edit Message Content"):
    message_content_input = discord.ui.TextInput(label="Message Content", style=discord.TextStyle.paragraph, max_length=2000, required=False)

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        new_content = self.message_content_input.value
        await self.embed_message.edit(content=new_content, embed=self.embed_message.embeds[0] if self.embed_message.embeds else None)
        await interaction.response.send_message("✅ Message content updated!", ephemeral=True)

# --- Modal for Send to User (sends message content + embed) ---

class SendToUserModal(discord.ui.Modal, title="Send to User"):
    user_id_input = discord.ui.TextInput(label="User ID", max_length=30, required=True, placeholder="Enter the user ID to DM")

    def __init__(self, embed_message: discord.Message):
        super().__init__()
        self.embed_message = embed_message

    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id_input.value.strip()
        try:
            user = await bot.fetch_user(int(user_id))
            if user is None:
                await interaction.response.send_message("❌ Could not find user with that ID.", ephemeral=True)
                return
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
            return

        content = self.embed_message.content or ""
        embed = self.embed_message.embeds[0] if self.embed_message.embeds else None

        try:
            await user.send(content=content, embed=embed)
            await interaction.response.send_message(f"✅ Sent message and embed to {user}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I can't DM that user. They might have DMs disabled.", ephemeral=True)

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

# --- The slash command ---

@bot.tree.command(name="dm", description="Send yourself a DM with an editable embed and message content")
async def dm(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Editable Embed Title",
        description="This is your editable embed description.\nUse the buttons below to edit parts of it.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Edit me using the buttons!")

    try:
        dm_channel = await interaction.user.create_dm()
        sent_message = await dm_channel.send(content="Your message content here (edit me)", embed=embed, view=None)
        view = EmbedEditView(embed_message=sent_message)
        await sent_message.edit(view=view)
        await interaction.response.send_message("📬 I sent you a DM with the editable embed and message!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I couldn't DM you. Please check your privacy settings.", ephemeral=True)

#






















































# === CONFIGURATION ===

CATEGORY_IDS = {
    "general": 1348205067462774814,
    "community": 1348205215723028490,
    "ai": 1348205704657244201,
    "report": 1348204608224231485,
    "closed": 1348206038758719522
}

ROLE_IDS = {
    "general": 1346578198749511700,
    "community": 1346578198749511700,
    "ai": 1346578198749511700,
    "report": 1346578198749511700
}

LOG_CHANNEL_ID = 1358405704393822288
TRANSCRIPT_CHANNEL_ID = 1366899644361343106

ticket_owners = {}
claimed_tickets = {}
last_user_messages = {}

# === UTILITIES ===

def make_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())

async def create_transcript(channel):
    messages = []
    async for msg in channel.history(oldest_first=True):
        content = msg.content or ""
        if msg.attachments:
            content += " " + " ".join([att.url for att in msg.attachments])
        messages.append(f"[{msg.created_at}] {msg.author}: {content}")
    transcript = "\n".join(messages) or "[No messages]"
    filename = f"transcript-{channel.name}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript)
    return filename

async def log_action(content):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=make_embed("Ticket Log", content))

async def move_to_closed(channel, user_id):
    await channel.edit(category=channel.guild.get_channel(CATEGORY_IDS["closed"]))
    user = channel.guild.get_member(user_id)
    transcript = await create_transcript(channel)

    try:
        await user.send(embed=make_embed("Your ticket has been closed", "Here is your transcript:"), file=discord.File(transcript))
    except:
        pass

    await bot.get_channel(TRANSCRIPT_CHANNEL_ID).send(
        embed=make_embed("Transcript Logged", f"Transcript from {channel.mention}"),
        file=discord.File(transcript)
    )
    os.remove(transcript)
    await log_action(f"Ticket {channel.name} closed and moved to Closed Tickets.")

# === MANAGE TICKET VIEW ===

class ManageTicketView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @ui.button(label="Claim", style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        if claimed_tickets.get(interaction.channel.id):
            return await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)

        claimed_tickets[interaction.channel.id] = interaction.user.id
        await interaction.response.send_message(embed=make_embed("Ticket Claimed", f"{interaction.user.mention} claimed this ticket."))
        await log_action(f"{interaction.user.mention} claimed ticket {interaction.channel.mention}")

    @ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id and interaction.user.id != claimed_tickets.get(interaction.channel.id):
            return await interaction.response.send_message("You cannot close this ticket.", ephemeral=True)
        await move_to_closed(interaction.channel, self.user_id)
        await interaction.response.send_message(embed=make_embed("Ticket Closed", f"Closed by {interaction.user.mention}."))

    @ui.button(label="Transcript", style=discord.ButtonStyle.primary)
    async def transcript(self, interaction: discord.Interaction, button: ui.Button):
        file = await create_transcript(interaction.channel)
        await interaction.response.send_message(embed=make_embed("Transcript Created", "Here is the transcript."), ephemeral=True)
        await bot.get_channel(TRANSCRIPT_CHANNEL_ID).send(embed=make_embed("Transcript", f"Transcript from {interaction.channel.mention}"), file=discord.File(file))
        os.remove(file)

    @ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: ui.Button):
        await log_action(f"{interaction.user.mention} deleted ticket {interaction.channel.name}")
        await interaction.channel.delete()

    @ui.button(label="Reopen", style=discord.ButtonStyle.success)
    async def reopen(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.channel.edit(category=interaction.guild.get_channel(CATEGORY_IDS["general"]))
        await interaction.response.send_message(embed=make_embed("Ticket Reopened", "Moved back to General Tickets"))

# === TICKET VIEWS ===

class TicketButton(ui.Button):
    def __init__(self, label, ticket_type):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=ticket_type)
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user

        # Prevent duplicate ticket
        for channel in interaction.guild.text_channels:
            if ticket_owners.get(channel.id) == user.id:
                await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
                return

        cat = interaction.guild.get_channel(CATEGORY_IDS[self.ticket_type])
        role = interaction.guild.get_role(ROLE_IDS[self.ticket_type])

        channel = await interaction.guild.create_text_channel(
            name=f"{self.ticket_type}-ticket-{user.name}",
            category=cat,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
            }
        )
        ticket_owners[channel.id] = user.id
        last_user_messages[channel.id] = datetime.datetime.utcnow()

        await channel.send(
            content=role.mention,
            embed=make_embed("Ticket Created", f"{user.mention}, your **{self.ticket_type}** ticket is open."),
            view=ManageTicketView(user.id)
        )
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
        await log_action(f"{user.mention} opened a {self.ticket_type} ticket: {channel.mention}")

class GeneralTicketButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton("General Support", "general"))
        self.add_item(TicketButton("Community Support", "community"))
        self.add_item(TicketButton("AI Support", "ai"))

class ReportTicketButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton("In-Game Report", "report"))

# === INACTIVITY TRACKING ===

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.channel.id in ticket_owners and message.author.id == ticket_owners[message.channel.id]:
        last_user_messages[message.channel.id] = datetime.datetime.utcnow()

@tasks.loop(minutes=10)
async def check_inactive_tickets():
    now = datetime.datetime.utcnow()
    for channel_id, user_id in ticket_owners.items():
        last = last_user_messages.get(channel_id)
        if last and (now - last) > timedelta(hours=2):
            channel = bot.get_channel(channel_id)
            user = channel.guild.get_member(user_id)
            if channel and user:
                try:
                    await channel.send(f"{user.mention}, are you still there? We’ll close the ticket if there’s no response.")
                    last_user_messages[channel_id] = now
                except:
                    pass

# === SLASH COMMANDS ===

@bot.tree.command(name="settickets", description="Send support ticket buttons (General, Community, AI).")
async def settickets(interaction: discord.Interaction):
    embed = make_embed("Support Tickets", "Click a button below to open a support ticket:")
    await interaction.response.send_message(embed=embed, view=GeneralTicketButtons())

@bot.tree.command(name="setreportticket", description="Send In-Game Report ticket button.")
async def setreportticket(interaction: discord.Interaction):
    embed = make_embed("In-Game Report", "Click the button below to open an in-game report ticket:")
    await interaction.response.send_message(embed=embed, view=ReportTicketButton())










































































# --- CONFIGURATION ---

API_KEY = os.getenv("API_KEY")
API_BASE = "https://api.policeroleplay.community/v1/server"
PRIV_ROLE_ID = 1316076187893891083
ROBLOX_USER_API = "https://users.roblox.com/v1/users"
LOGS_CHANNEL_ID = 1381267054354632745
ENDPOINTS = ["modcalls", "killlogs", "joinlogs"]
WELCOME_TEMPLATE = "Welcome to the server!"
KICK_REASON = "Username not allowed (starts with All or Others)"
PLAYERCOUNT_VC_ID = 1381697147895939233  # VC that will show player count
QUEUE_VC_ID = 1381697165562347671        # VC that will show queue size
PLAYERCOUNT_PREFIX = "「🎮」In Game:"
QUEUE_PREFIX = "「⏳」In Queue:"
DISCORD_CHANNEL_ID = 1381267054354632745  # your target channel ID
STAFF_ROLE_ID = 1375985192174354442  # the Discord role ID to exempt users

# Example config: vehicle name mapped to allowed Discord role IDs
RESTRICTED_VEHICLES = {
    "Bugatti Veyron": [123456789012345678],  # VIP role
    "Tesla Roadster": [234567890123456789],  # Booster role
}

# Roblox-Discord links
ROBLOX_DISCORD_LINKS = {
    "PlayerName123": 345678901234567890,  # Discord user ID
    "VIPUser987": 123456789012345678,     # This one has VIP
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

# Discord channel IDs for logging
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
    emoji = "<:error:1383587321294884975>"

    messages = {
        0:    f"{emoji} **0 – Unknown Error**: Unknown error occurred. If this is persistent, contact PRC via an API ticket.",
        100:  f"{emoji} **100 – Continue**: The server has received the request headers, and the client should proceed.",
        101:  f"{emoji} **101 – Switching Protocols**: Protocol switching in progress.",
        200:  f"{emoji} **200 – OK**: The request was successful.",
        201:  f"{emoji} **201 – Created**: The request has been fulfilled and a new resource was created.",
        204:  f"{emoji} **204 – No Content**: The server successfully processed the request but returned no content.",
        400:  f"{emoji} **400 – Bad Request**: Bad request.",
        401:  f"{emoji} **401 – Unauthorized**: Authentication is required or has failed.",
        403:  f"{emoji} **403 – Unauthorized**: Unauthorized access.",
        404:  f"{emoji} **404 – Not Found**: The requested resource could not be found.",
        405:  f"{emoji} **405 – Method Not Allowed**: The HTTP method is not allowed for this endpoint.",
        408:  f"{emoji} **408 – Request Timeout**: The server timed out waiting for the request.",
        409:  f"{emoji} **409 – Conflict**: The request could not be processed because of a conflict.",
        410:  f"{emoji} **410 – Gone**: The resource requested is no longer available.",
        415:  f"{emoji} **415 – Unsupported Media Type**: The server does not support the media type.",
        418:  f"{emoji} **418 – I'm a teapot**: The server refuses to brew coffee in a teapot.",
        422:  f"{emoji} **422 – No Players**: The private server has no players in it.",
        429:  f"{emoji} **429 – Too Many Requests**: You are being rate limited.",
        500:  f"{emoji} **500 – Internal Server Error**: Problem communicating with Roblox.",
        501:  f"{emoji} **501 – Not Implemented**: The server does not recognize the request method.",
        502:  f"{emoji} **502 – Bad Gateway**: The server received an invalid response from the upstream server.",
        503:  f"{emoji} **503 – Service Unavailable**: The server is not ready to handle the request.",
        504:  f"{emoji} **504 – Gateway Timeout**: The server did not get a response in time.",
        1001: f"{emoji} **1001 – Communication Error**: An error occurred communicating with Roblox / the in-game private server.",
        1002: f"{emoji} **1002 – System Error**: An internal system error occurred.",
        2000: f"{emoji} **2000 – Missing Server Key**: You did not provide a server-key.",
        2001: f"{emoji} **2001 – Bad Server Key Format**: You provided an incorrectly formatted server-key.",
        2002: f"{emoji} **2002 – Invalid Server Key**: You provided an invalid (or expired) server-key.",
        2003: f"{emoji} **2003 – Invalid Global API Key**: You provided an invalid global API key.",
        2004: f"{emoji} **2004 – Banned Server Key**: Your server-key is currently banned from accessing the API.",
        3001: f"{emoji} **3001 – Missing Command**: You did not provide a valid command in the request body.",
        3002: f"{emoji} **3002 – Server Offline**: The server you are attempting to reach is currently offline (has no players).",
        4001: f"{emoji} **4001 – Rate Limited**: You are being rate limited.",
        4002: f"{emoji} **4002 – Command Restricted**: The command you are attempting to run is restricted.",
        4003: f"{emoji} **4003 – Prohibited Message**: The message you're trying to send is prohibited.",
        9998: f"{emoji} **9998 – Resource Restricted**: The resource you are accessing is restricted.",
        9999: f"{emoji} **9999 – Module Outdated**: The module running on the in-game server is out of date, please kick all and try again.",
    }

    base_message = messages.get(http_status, f"{emoji} **{http_status} – Unknown Error**: An unexpected error occurred.")
    if api_code:
        base_message += f"\nAPI code: {api_code}"
    return base_message

# === PRC COMMAND ===
@bot.tree.command(name="erlc_command", description="Run a server command like :h, :m, :mod")
@discord.app_commands.describe(command="The command to run (e.g. ':h Hello', ':m message', ':mod')")
async def erlc_command(interaction: discord.Interaction, command: str):
    await interaction.response.defer()

    lowered = command.lower()

    # Block ban/unban/kick commands
    if any(word in lowered for word in ["ban", "unban", "kick"]):
        await interaction.followup.send("❌ You are not allowed to run ban, unban, or kick commands.")
        return

    # If command starts with ":log ", treat it as a log message to send in game
    if lowered.startswith(":log "):
        message_to_log = command[5:].strip()
        if not message_to_log:
            await interaction.followup.send("❌ You must provide a message after ':log'.")
            return

        in_game_command = f":say [LOG] {message_to_log}"

        embed = discord.Embed(
            title="🛠 In-Game Log Message Sent",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
        embed.add_field(name="Message", value=message_to_log, inline=False)
        embed.set_footer(text="PRC Command Log")
        await send_embed(COMMAND_LOG_CHANNEL_ID, embed)

        payload = {"command": in_game_command}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{API_BASE}/command", headers=HEADERS_POST, json=payload) as resp:
                    if resp.status != 200:
                        try:
                            data = await resp.json()
                            api_code = data.get("code")
                        except:
                            api_code = None
                        await interaction.followup.send(get_error_message(resp.status, api_code))
                        return
            except Exception as e:
                await interaction.followup.send(f"⚠️ Exception occurred: {e}")
                return

        await interaction.followup.send(f"✅ Log message sent in-game: {message_to_log}")
        return

    # Regular command flow for other commands
    embed = discord.Embed(
        title="🛠 Command Executed",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
    embed.add_field(name="Command", value=f"{command}", inline=False)
    embed.set_footer(text="PRC Command Log")
    await send_embed(COMMAND_LOG_CHANNEL_ID, embed)

    payload = {"command": command}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{API_BASE}/command", headers=HEADERS_POST, json=payload) as resp:
                if resp.status != 200:
                    try:
                        data = await resp.json()
                        api_code = data.get("code")
                    except:
                        api_code = None
                    await interaction.followup.send(get_error_message(resp.status, api_code))
                    return
        except Exception as e:
            await interaction.followup.send(f"⚠️ Exception occurred: {e}")
            return

    await interaction.followup.send(f"✅ Command {command} sent successfully.")


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
            title="📥 Player Join/Leave",
            color=discord.Color.green() if joined else discord.Color.red(),
            timestamp=datetime.fromtimestamp(ts, UTC)
        )
        embed.add_field(name="Player", value=player, inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.set_footer(text="PRC Join/Leave Logs")

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
        embed.set_footer(text="PRC Kill Logs")

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
        title="📜 Join/Leave Logs",
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
        title="📜 Command Logs",
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
                await interaction.followup.send(f"❌ Failed to fetch Roblox user. Status: {resp.status}")
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







# Colors
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blue()
BLANK_COLOR = discord.Color.blurple()

# Global session, created in on_ready
session: aiohttp.ClientSession | None = None

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
            await interaction.response.send_message("⚠️ You can't use this button.", ephemeral=True)
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
        name="🧾 Basic Info",
        value=(
            f"> **Join Code:** [{server['JoinKey']}](https://policeroleplay.community/join/{server['JoinKey']})\n"
            f"> **Players:** {server['CurrentPlayers']}/{server['MaxPlayers']}\n"
            f"> **Queue:** {len(queue)}"
        ),
        inline=False
    )
    embed.add_field(
        name="👮 Staff Info",
        value=(
            f"> **Moderators:** {len(mods)}\n"
            f"> **Administrators:** {len(admins)}\n"
            f"> **Staff in Server:** {len(staff)}"
        ),
        inline=False
    )
    embed.add_field(
        name="👑 Server Ownership",
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
        await interaction.followup.send("❌ Failed to fetch server information.")



@erlc_group.command(name="players", description="See all players in the server.")
@app_commands.describe(filter="Filter players by username prefix (optional)")
async def players(interaction: discord.Interaction, filter: str = None):
    await interaction.response.defer()

    global session
    if session is None:
        await interaction.followup.send("HTTP session not ready.")
        return

    headers = {"server-key": API_KEY}
    async with session.get(f"{API_BASE}/players", headers=headers) as resp:
        if resp.status != 200:
            await interaction.followup.send(f"Failed to fetch players (status {resp.status})")
            return
        players_data = await resp.json()

    async with session.get(f"{API_BASE}/queue", headers=headers) as resp:
        if resp.status != 200:
            await interaction.followup.send(f"Failed to fetch queue (status {resp.status})")
            return
        queue_data = await resp.json()

    staff = []
    actual_players = []

    for p in players_data:
        try:
            username, id_str = p["Player"].split(":")
            player_id = int(id_str)
        except Exception:
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
            f"[{p['username']} ({p['team']})](https://roblox.com/users/{p['id']}/profile)" for p in players_list
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
        if any(role.id == STAFF_ROLE_ID for role in member.roles):
            return True
        raise app_commands.CheckFailure("You do not have permission to use this command.")
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

async def prc_get(endpoint):
    global session
    if session is None:
        raise Exception("HTTP session not initialized")
    headers = {"server-key": API_KEY, "Accept": "*/*"}
    url = f"{API_BASE}{endpoint}"
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            text = await resp.text()
            raise Exception(f"PRC API error {resp.status}: {text}")

@erlc_group.command(name="vehicles", description="Show vehicles currently in the server")
async def vehicles(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        players = await prc_get("/server/players")
        vehicles = await prc_get("/server/vehicles")
    except Exception as e:
        return await interaction.followup.send(f"Error fetching PRC data: {e}")

    if not vehicles:
        embed = discord.Embed(
            title="Server Vehicles 0",
            description="> There are no active vehicles in your server.",
            color=discord.Color.blue()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
        return await interaction.followup.send(embed=embed)

    players_dict = {p['Player'].split(":")[0]: p for p in players}
    matched = []
    for vehicle in vehicles:
        owner = vehicle.get("Owner")
        if owner in players_dict:
            matched.append((vehicle, players_dict[owner]))

    description_lines = []
    for veh, plr in matched:
        username = plr['Player'].split(":")[0]
        roblox_id = plr['Player'].split(":")[1]
        description_lines.append(f"[{username}](https://roblox.com/users/{roblox_id}/profile) - {veh['Name']} **({veh['Texture']})**")

    description = "\n".join(description_lines)
    embed = discord.Embed(
        title=f"Server Vehicles [{len(vehicles)}/{len(players)}]",
        description=description,
        color=discord.Color.blue()
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.followup.send(embed=embed)

@discord_group.command(name="check", description="Check if players in ER:LC are in Discord")
async def check(interaction: discord.Interaction):
    await interaction.response.defer()

    def extract_roblox_name(name: str) -> str:
        return name.split(" | ", 1)[1].lower() if " | " in name else name.lower()

    try:
        players = await prc_get("/server/players")
    except Exception as e:
        return await interaction.followup.send(f"Error fetching PRC data: {e}")

    if not players:
        embed = discord.Embed(
            title="players in ER:LC are not Discord",
            description="> No players found in the server.",
            color=discord.Color.blue()
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="SWAT Roleplay Community")
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
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

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
                        description=f"Failed to fetch bans. Status code: {resp.status}",
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
    """Returns [Name](link) or just name"""
    try:
        name, user_id = player_str.split(":")
        return f"[{name}](https://www.roblox.com/users/{user_id}/profile)"
    except:
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

HEADERS_POST = {
    "server-key": API_KEY,
    "Content-Type": "application/json"
}

CHANNEL_ID = 1382852068816978092
last_shutdown_call = 0  # global cooldown tracker


async def send_ssd_and_kick(channel: discord.TextChannel):
    global last_shutdown_call
    if time.time() - last_shutdown_call < 5:
        return  # Ignore if called again within 5 seconds
    last_shutdown_call = time.time()

    shutdown_message = {
        "command": ":m ❗ SWAT Roleplay Community has unfortunately chosen to SSD. You must leave the game at this time and only rejoin during an SSU. Failure to leave within 3 minutes will result in being kicked. If you have any questions, call !mod. Thank you! ❗"
    }

    try:
        response = requests.post(f"{API_BASE}/command", headers=HEADERS_POST, json=shutdown_message)
        if response.status_code == 200:
            embed = discord.Embed(
                title="SSD Message Sent ✅",
                description="The shutdown message was successfully sent. Waiting 4 minutes before kicking all players...",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players in Server ⚠️",
                description="There are no players currently in the server to receive the SSD message.",
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)
            return
        else:
            embed = discord.Embed(
                title="Failed to Send SSD Message ❌",
                description=f"API responded with status code `{response.status_code}`.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            return
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending SSD Message ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
        return

    await asyncio.sleep(240)  # Wait 4 minutes

    kick_all_command = {"command": ":kick all"}
    try:
        response = requests.post(f"{API_BASE}/command", headers=HEADERS_POST, json=kick_all_command)
        if response.status_code == 200:
            embed = discord.Embed(
                title="Kick All Sent ✅",
                description="All players have been kicked from the server.",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players to Kick ⚠️",
                description="Kick all failed — no players were left in the server.",
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Failed to Kick ❌",
                description=f"API responded with status code `{response.status_code}` when kicking.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending Kick Command ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)


@bot.tree.command(name="ssd", description="Send a server shutdown message to the ER:LC server")
async def ssd(interaction: discord.Interaction):
    await interaction.response.defer()
    await send_ssd_and_kick(interaction.channel)


@bot.event
async def on_message(message: discord.Message):
    global last_shutdown_call

    if message.channel.id != CHANNEL_ID:
        return

    if message.webhook_id and message.embeds:
        embed = message.embeds[0]
        if embed.description and ":log ssd" in embed.description.lower():
            # Skip if SSD triggered recently (already handled by slash command)
            if time.time() - last_shutdown_call < 5:
                return
            await send_ssd_and_kick(message.channel)

    await bot.process_commands(message)

# --------------------------------

REQUIRED_ROLE_ID = 1316076193459474525  # Staff role required to run the command

async def send_the_emergency_shutdown_message(channel: discord.TextChannel):
    shutdown_message = {
        "command": ":m ❗ The SWAT Roleplay Community owner has done an emergency server shutdown. You must leave the game. Failure to leave within 1.5 minutes will result in being kicked. Thank you! ❗"
    }

    try:
        response = requests.post(f"{API_BASE}/command", headers=HEADERS_POST, json=shutdown_message)
        if response.status_code == 200:
            embed = discord.Embed(
                title="SSD Message Sent ✅",
                description="The emergency shutdown message was successfully sent. Waiting 1.5 minutes before kicking all players...",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players in Server ⚠️",
                description="There are no players currently in the server to receive the emergency shutdown message.",
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)
            return
        else:
            embed = discord.Embed(
                title="Failed to Send the emergency shutdown message ❌",
                description=f"API responded with status code `{response.status_code}`.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            return
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending the emergency shutdown message ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
        return

    await asyncio.sleep(90)  # wait 1.5 minutes before kicking

    kick_all_command = {
        "command": ":kick all"
    }

    try:
        response = requests.post(f"{API_BASE}/command", headers=HEADERS_POST, json=kick_all_command)
        if response.status_code == 200:
            embed = discord.Embed(
                title="Kick All Sent ✅",
                description="All players have been kicked from the server.",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players to Kick ⚠️",
                description="Kick all failed — no players were left in the server.",
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Failed to Kick ❌",
                description=f"API responded with status code `{response.status_code}` when kicking.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending Kick Command ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)


@erlc_group.command(name="shutdown", description="Send a server shutdown message to the ER:LC server")
async def shutdown_erlc(interaction: discord.Interaction):
    member = interaction.guild.get_member(interaction.user.id)
    REQUIRED_ROLE_ID = 1316076193459474525

    if not member or REQUIRED_ROLE_ID not in [role.id for role in member.roles]:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Permission Denied ❌",
                description="You must have the Staff role to use this command.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    await interaction.response.defer()
    await send_the_emergency_shutdown_message(interaction.channel)

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
                print(f"⚠️ Failed to kick {player_name}.")
        else:
            if player_name not in welcomed_players:
                if send_welcome(player_name):
                    print(f"✅ Welcomed {player_name}")
                    welcomed_players.add(player_name)
                else:
                    print(f"❌ Failed to welcome {player_name}")

        handled_usernames.add(player_name)

@tasks.loop(seconds=100)
async def check_log_commands():
    logs = fetch_command_logs()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("❌ Guild not found")
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
            print(f"❌ Invalid VC abbreviation: {abbrev}")
            continue

        discord_id = ROBLOX_TO_DISCORD.get(target_username)
        if not discord_id:
            print(f"⚠️ No Discord user linked for {target_username}")
            continue

        member = guild.get_member(discord_id)
        if not member:
            print(f"⚠️ Member not in guild: {discord_id}")
            continue

        if not member.voice or not member.voice.channel:
            print(f"ℹ️ {member.display_name} not in VC")
            continue

        try:
            await member.move_to(guild.get_channel(vc_id))
            print(f"✅ Moved {member.display_name} to {abbrev}")
        except Exception as e:
            print(f"❌ Failed to move {member.display_name}: {e}")

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
        print("❌ Failed to fetch player count:", e)
        player_count = 0

    # Get queue count
    try:
        queue_response = requests.get(f"{API_BASE}/queue", headers=headers)
        queue_count = len(queue_response.json()) if queue_response.status_code == 200 else 0
    except Exception as e:
        print("❌ Failed to fetch queue:", e)
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
        print("❌ Failed to update VC names:", e)

async def check_vehicle_restrictions(bot):
    headers = {"server-key": "YOUR_SERVER_KEY"}
    try:
        response = requests.get("https://api.policeroleplay.community/v1/server/vehicles", headers=headers)
        vehicles = response.json()
    except Exception as e:
        print("❌ Failed to fetch vehicle list:", e)
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
            print(f"❌ Member not found in Discord: {player_name}")
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
            print(f"⚠️ Warned {player_name} for unauthorized vehicle use.")

@bot.tree.command(name="set_restriction")
@app_commands.describe(vehicle="Vehicle name", role="Role required")
async def set_restriction(interaction: discord.Interaction, vehicle: str, role: discord.Role):
    RESTRICTED_VEHICLES[vehicle] = [role.id]
    await interaction.response.send_message(f"✅ Set restriction: `{vehicle}` → `{role.name}`", ephemeral=True)

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
            print("Channel not found")
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
            if any(role.id == STAFF_ROLE_ID for role in member.roles):
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











# Replace these IDs with your actual IDs
GUILD_ID = 1343179590247645205
SHIFT_ROLE_ID = 1343299303459913761
BREAK_ROLE_ID = 1343299319939207208
LOG_CHANNEL_ID = 1381409066156425236

@bot.tree.command(name="shift_manage", description="Manage your shift status")
async def shift_manage(interaction: discord.Interaction):
    # Only allow in your guild
    if interaction.guild_id != GUILD_ID:
        await interaction.response.send_message("This command can only be used in the designated server.", ephemeral=True)
        return

    # Permission check example: only members with Manage Roles can open the panel
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You do not have permission to manage roles.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Shift Management",
        description="Click a button below to manage your shift status.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Use the buttons to toggle your shift status.")

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Start Shift", style=discord.ButtonStyle.green, custom_id="start_shift"))
    view.add_item(discord.ui.Button(label="End Shift", style=discord.ButtonStyle.red, custom_id="end_shift"))
    view.add_item(discord.ui.Button(label="Take Break", style=discord.ButtonStyle.blurple, custom_id="take_break"))
    view.add_item(discord.ui.Button(label="Return from Break", style=discord.ButtonStyle.blurple, custom_id="return_break"))

    await interaction.response.send_message(embed=embed, view=view)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    # Only handle component (button) interactions with custom_id
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id")
    if not custom_id:
        return

    # Check guild and member exist
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        await interaction.response.send_message("❌ Guild not found.", ephemeral=True)
        return

    member = guild.get_member(interaction.user.id)
    if member is None:
        await interaction.response.send_message("❌ Could not find you in the server.", ephemeral=True)
        return

    role_shift = guild.get_role(SHIFT_ROLE_ID)
    role_break = guild.get_role(BREAK_ROLE_ID)
    log_channel = guild.get_channel(LOG_CHANNEL_ID)

    # Check roles exist
    if role_shift is None or role_break is None:
        await interaction.response.send_message("❌ One or more required roles not found. Please check role IDs.", ephemeral=True)
        return

    # Defer response for button interaction to avoid "interaction failed"
    await interaction.response.defer(ephemeral=True)

    try:
        if custom_id == "start_shift":
            if role_shift not in member.roles:
                await member.add_roles(role_shift, reason="Started shift")
                if role_break in member.roles:
                    await member.remove_roles(role_break, reason="Break ended due to shift start")
                if log_channel:
                    await log_channel.send(f"✅ {member.mention} has **started their shift**.")
                await interaction.followup.send("You have started your shift. ✅", ephemeral=True)
            else:
                await interaction.followup.send("You are already on shift.", ephemeral=True)

        elif custom_id == "end_shift":
            if role_shift in member.roles:
                await member.remove_roles(role_shift, reason="Ended shift")
                if role_break in member.roles:
                    await member.remove_roles(role_break, reason="Ended shift break cleanup")
                if log_channel:
                    await log_channel.send(f"❌ {member.mention} has **ended their shift**.")
                await interaction.followup.send("You have ended your shift. ❌", ephemeral=True)
            else:
                await interaction.followup.send("You are not currently on shift.", ephemeral=True)

        elif custom_id == "take_break":
            if role_shift not in member.roles:
                await interaction.followup.send("You must be on shift to take a break.", ephemeral=True)
                return

            if role_break not in member.roles:
                await member.add_roles(role_break, reason="Started break")
                if log_channel:
                    await log_channel.send(f"⏸️ {member.mention} has **started a break**.")
                await interaction.followup.send("You are now on break. ⏸️", ephemeral=True)
            else:
                await interaction.followup.send("You are already on break.", ephemeral=True)

        elif custom_id == "return_break":
            if role_break in member.roles:
                await member.remove_roles(role_break, reason="Returned from break")
                if log_channel:
                    await log_channel.send(f"▶️ {member.mention} has **returned from break**.")
                await interaction.followup.send("You have returned from your break. ▶️", ephemeral=True)
            else:
                await interaction.followup.send("You are not currently on a break.", ephemeral=True)
        else:
            await interaction.followup.send("Unknown button action.", ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send("❌ I do not have permission to manage your roles.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)





























# Join voice channel command
@bot.tree.command(name="join_voice_channel", description="Make the bot join your voice channel")
async def join_voice_channel(interaction: discord.Interaction):
    voice_state = interaction.user.voice
    if not voice_state or not voice_state.channel:
        await interaction.response.send_message("❌ You are not connected to any voice channel.", ephemeral=True)
        return

    channel = voice_state.channel
    voice_client = interaction.guild.voice_client

    if voice_client:
        if voice_client.channel.id == channel.id:
            await interaction.response.send_message(f"✅ I'm already connected to **{channel.name}**.", ephemeral=True)
            return
        try:
            await voice_client.move_to(channel)
            await interaction.response.send_message(f"✅ Moved to **{channel.name}**.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"❌ Failed to move: {e}", ephemeral=True)
    else:
        try:
            await channel.connect()
            await interaction.response.send_message(f"✅ Joined **{channel.name}**.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"❌ Failed to connect: {e}", ephemeral=True)

# Leave voice channel command
@bot.tree.command(name="leave_voice_channel", description="Make the bot leave its current voice channel")
async def leave_voice_channel(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_connected():
        try:
            await voice_client.disconnect()
            await interaction.response.send_message("👋 Left the voice channel.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"❌ Failed to disconnect: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ I'm not connected to any voice channel.", ephemeral=True)

# Additional commands

@bot.tree.command(name="pause_voice", description="Pause the currently playing audio")
async def pause_voice(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ Paused the audio.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ No audio is currently playing.", ephemeral=True)

@bot.tree.command(name="resume_voice", description="Resume paused audio")
async def resume_voice(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ Resumed the audio.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ No audio is currently paused.", ephemeral=True)

@bot.tree.command(name="stop_voice", description="Stop the audio and disconnect from voice channel")
async def stop_voice(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if voice_client:
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        try:
            await voice_client.disconnect()
            await interaction.response.send_message("🛑 Stopped and left the voice channel.", ephemeral=True)
        except discord.DiscordException as e:
            await interaction.response.send_message(f"❌ Failed to disconnect: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ I'm not connected to any voice channel.", ephemeral=True)



































































































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

        await interaction.response.edit_message(content="✅ Sent to staff.", view=None)

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
        await interaction.response.send_message("✅ Closed. Thank you!")

async def send_transcript(channel, user_id):
    output = ""
    async for msg in channel.history(limit=None, oldest_first=True):
        output += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

    transcript_file = discord.File(io.BytesIO(output.encode()), filename="transcript.txt")
    log_channel = bot.get_channel(TRANSCRIPT_LOG_CHANNEL)
    user = await bot.fetch_user(user_id)

    if log_channel:
        await log_channel.send(f"📝 Transcript for user `{user}`", file=transcript_file)

    try:
        await user.send("📄 Here's the transcript of your modmail session:", file=transcript_file)
    except:
        pass

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
                await message.channel.send(f"❌ Could not message user: {e}")

# ========== Slash Commands ==========
@bot.tree.command(name="claim", description="Claim this modmail thread.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def claim(interaction: discord.Interaction):
    topic = interaction.channel.topic
    if not topic or not topic.startswith("ID:"):
        return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))
    user = await bot.fetch_user(user_id)
    claimed_by[user_id] = interaction.user.id
    await interaction.response.send_message(f"✅ Claimed by {interaction.user.mention}")
    try:
        await user.send(f"👮 Your modmail was claimed by {interaction.user.name}.")
    except:
        pass

@bot.tree.command(name="close", description="Close and archive this thread.")
@app_commands.checks.has_any_role(*STAFF_ROLE_IDS)
async def close(interaction: discord.Interaction):
    topic = interaction.channel.topic
    if not topic or not topic.startswith("ID:"):
        return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))
    await interaction.response.send_message("🔒 Closing and sending transcript...")
    await interaction.channel.send("🔒 Closed by staff.")
    try:
        user = await bot.fetch_user(user_id)
        await user.send("🔒 Your modmail thread has been closed by staff.")
    except:
        pass
    await send_transcript(interaction.channel, user_id)
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
        return await interaction.response.send_message("❌ Not a modmail thread.", ephemeral=True)

    user_id = int(topic.replace("ID:", ""))
    await send_transcript(interaction.channel, user_id)
    await interaction.response.send_message("📄 Transcript sent.")

















































































































































































































LOGS_CONFIG_FILE = 'logs_config.json'

def load_logs_config():
    if os.path.exists(LOGS_CONFIG_FILE):
        with open(LOGS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_logs_config(data):
    with open(LOGS_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def send_log(bot, guild: discord.Guild, embed: discord.Embed):
    config = load_logs_config()
    webhook_url = config.get(str(guild.id))
    if webhook_url:
        webhook = discord.Webhook.from_url(webhook_url, session=bot.http._HTTPClient__session)
        await webhook.send(embed=embed, username=bot.user.name, avatar_url=bot.user.display_avatar.url)

@bot.tree.command(name="logs_set", description="Set the logging channel")
@app_commands.describe(channel="Channel to log events in")
async def logs_set(interaction: discord.Interaction, channel: discord.TextChannel):
    if not channel.permissions_for(interaction.guild.me).manage_webhooks:
        return await interaction.response.send_message("❌ I need Manage Webhooks permission there.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    webhooks = await channel.webhooks()
    webhook = next((w for w in webhooks if w.user == bot.user), None)
    if webhook is None:
        webhook = await channel.create_webhook(name=bot.user.name, avatar=await bot.user.display_avatar.read())

    config = load_logs_config()
    config[str(interaction.guild.id)] = webhook.url
    save_logs_config(config)

    embed = discord.Embed(title="✅ Logging Enabled", description=f"Logs will be sent to {channel.mention}", color=discord.Color.green())
    await webhook.send(embed=embed, username=bot.user.name, avatar_url=bot.user.display_avatar.url)
    await interaction.followup.send(f"✅ Logs set in {channel.mention}", ephemeral=True)

### LOG EVENTS BELOW ###

# Member join/leave
@bot.event
async def on_member_join(member):
    embed = discord.Embed(title="👤 Member Joined", description=f"{member.mention} joined.", color=discord.Color.green())
    embed.set_footer(text=f"ID: {member.id}")
    await send_log(bot, member.guild, embed)

@bot.event
async def on_member_remove(member):
    embed = discord.Embed(title="👤 Member Left", description=f"{member.mention} left or was kicked.", color=discord.Color.red())
    embed.set_footer(text=f"ID: {member.id}")
    await send_log(bot, member.guild, embed)

@bot.event
async def on_member_update(before, after):
    # Nickname change
    if before.nick != after.nick:
        embed = discord.Embed(title="✏️ Nickname Changed", color=discord.Color.orange())
        embed.add_field(name="Before", value=before.nick or "None", inline=True)
        embed.add_field(name="After", value=after.nick or "None", inline=True)
        embed.set_footer(text=f"{after} • ID: {after.id}")
        await send_log(bot, after.guild, embed)

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
        await send_log(bot, after.guild, embed)

    # Timeout change
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            title = "🔕 Member Timed Out"
            color = discord.Color.dark_red()
        else:
            title = "🔔 Timeout Removed"
            color = discord.Color.green()
        embed = discord.Embed(title=title, description=f"{after.mention}", color=color)
        await send_log(bot, after.guild, embed)

# Server Boost
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        embed = discord.Embed(title="🚀 Server Boost", description=f"{after.mention} just boosted the server!", color=discord.Color.purple())
        await send_log(bot, after.guild, embed)

# Ban / unban
@bot.event
async def on_member_ban(guild, user):
    embed = discord.Embed(title="🔨 Banned", description=f"{user} was banned", color=discord.Color.red())
    await send_log(bot, guild, embed)

@bot.event
async def on_member_unban(guild, user):
    embed = discord.Embed(title="♻️ Unbanned", description=f"{user} was unbanned", color=discord.Color.green())
    await send_log(bot, guild, embed)

# Messages
@bot.event
async def on_message_delete(message):
    if message.guild and not message.author.bot:
        embed = discord.Embed(title="🗑️ Message Deleted", description=f"In {message.channel.mention}", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Content", value=message.content or "*No content*", inline=False)
        await send_log(bot, message.guild, embed)

@bot.event
async def on_message_edit(before, after):
    if before.guild and before.content != after.content:
        embed = discord.Embed(title="✏️ Message Edited", description=f"In {before.channel.mention}", color=discord.Color.orange())
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="Before", value=before.content or "*Empty*", inline=False)
        embed.add_field(name="After", value=after.content or "*Empty*", inline=False)
        await send_log(bot, before.guild, embed)

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel):
        embed = discord.Embed(title="📁 Channel Created", description=f"{channel.mention} was created", color=discord.Color.green())
        await send_log(bot, channel.guild, embed)

@bot.event
async def on_guild_channel_delete(channel):
    embed = discord.Embed(title="🗑️ Channel Deleted", description=f"#{channel.name} was deleted", color=discord.Color.red())
    await send_log(bot, channel.guild, embed)

@bot.event
async def on_guild_channel_update(before, after):
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
        await send_log(bot, before.guild, embed)


































# Remove the default help command so we can define our own
bot.remove_command("help")

@bot.tree.command(name="help", description="Show all available commands and their descriptions")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands List",
        description="Explore the available commands grouped by category. Use </command:1381009162334503014> for more details.",
        color=discord.Color.blurple()
    )

    # General commands
    embed.add_field(
        name="**🛠️ General**",
        value="</ping:1381009161621475383> - Check if the bot is online\n"
              "</say:1381009161621475384> - Let the bot say something\n"
              "</embed:1381009161621475387> - Create a custom embed message\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    # Moderation commands
    embed.add_field(
        name="**⚙️ Moderation**",
        value="</slowmode:1381009161621475385> - Set slowmode in a channel\n"
              "</clear:1381009162170929406> - Clear messages in a channel\n"
              "</nickname:1381009161814540386> - Change a user's nickname\n"
              "</warn:1381009161621475378> - Warn a member\n"
              "</warnings:1381009161621475380> - View warnings for a member\n"
              "</unwarn:1381009161621475379> - Remove a warning\n"
              "</clear_all_warnings:1381009161621475382> - Clear all warnings\n"
              "</shutdown:1381278435938271296> - Shutdown the bot (OWNER ONLY)\n"
              "</kick:1381009161961078864> - Kick a member\n"
              "</ban:1381009161961078865> - Ban a member\n"
              "</unban:1381009162170929405> - Unban a member\n"
              "</mute:1381009161961078866> - Mute a member\n"
              "</unmute:1381009162170929404> - Unmute a member\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    # ER:LC Management commands
    embed.add_field(
        name="**🚨 ER:LC Management**",
        value="</session vote:1381009161961078863> - ER:LC commands\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    # Channel Management commands
    embed.add_field(
        name="**🔒 Channel Management**",
        value="</lock:1381009162170929408> - Lock the current channel\n"
              "</unlock:1381009162170929407> - Unlock the current channel\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    # AFK Management commands
    embed.add_field(
        name="**⏰ AFK Management**",
        value="</afk:1381009161814540380> - Set yourself as AFK\n"
              "</unafk:1381009161814540381> - Remove your AFK status\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    # Other commands part 1
    embed.add_field(
        name="**💼 Other (Part 1)**",
        value="</roleinfo:1381009161814540384> - Info about a role\n"
              "</invite:1381009161814540385> - Get bot invite\n"
              "</server_info:1381009161814540382> - Info about the server\n"
              "</user_info:1381009161814540383> - Info about a user\n"
              "</remindme:1381009161814540388> - Set a reminder\n"
              "</servericon:1381009161814540387> - Get server's icon\n"
              "</suggestion:1381009161814540389> - Submit a suggestion\n"
              "</staff_suggestion:1381009161961078857> - Suggestion for staff\n"
              "</staff_feedback:1381009161961078858> - Feedback for staff\n"
              "</events:1381009161961078861> - View upcoming events",
        inline=False
    )

    # Other commands part 2
    embed.add_field(
        name="**💼 Other (Part 2)**",
        value="</event:1381009161961078860> - Create an event\n"
              "</mod_panel:1381009161961078862> - Open mod panel\n"
              "</report:1381009162170929409> - Report a user\n"
              "</poll:1381009162170929410> - Create a yes/no poll\n"
              "</setreportticket:1381009162170929412> - In-Game Report button\n"
              "</settickets:1381009162170929411> - Support ticket buttons\n"
              "</up_time:1381009161621475386> - Bot uptime\n"
              "</dm:1381005826558267392> - DM with editable embed\n"
              "Use </command:1381009162334503014> for more details.",
        inline=False
    )

    embed.set_footer(text="The SWAT Roleplay Community | Use /command [command name] for more details.")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/1234567890/thumbnail_image.png")

    await interaction.response.send_message(embed=embed)

# prefix command for help
@bot.command(name="help", description="Show all available commands and their descriptions")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="Bot Commands List",
        description="Explore the available commands grouped by category. Use `/command [command name]` for more details.",
        color=discord.Color.blurple()
    )

    # General commands
    embed.add_field(
        name="**🛠️ General**",
        value="`ping`, `say`, `embed`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # Moderation commands
    embed.add_field(
        name="**⚙️ Moderation**",
        value="`slowmode`, `clear`, `nickname`, `warn`, `warnings`, `unwarn`, `clear_all_warnings`, `shutdown`, "
              "`kick`, `ban`, `unban`, `mute`, `unmute`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # ER:LC Management commands
    embed.add_field(
        name="**🚨 ER:LC Management**",
        value="`session vote`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # Channel Management commands
    embed.add_field(
        name="**🔒 Channel Management**",
        value="`lock`, `unlock`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # AFK Management commands
    embed.add_field(
        name="**⏰ AFK Management**",
        value="`afk`, `unafk`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # Other commands part 1
    embed.add_field(
        name="**💼 Other (Part 1)**",
        value="`roleinfo`, `invite`, `server_info`, `user_info`, `remindme`, "
              "`servericon`, `suggestion`, `staff_suggestion`, `staff_feedback`, "
              "`events`\nUse `/command [command name]` for more details.",
        inline=False
    )

    # Other commands part 2
    embed.add_field(
        name="**💼 Other (Part 2)**",
        value="`event`, `mod_panel`, `report`, `poll`, `setreportticket`, "
              "`settickets`, `up_time`, `dm`\nUse "
                "`/command [command name]` for more details.",
        inline=False
    )
    embed.set_footer(text="The SWAT Roleplay Community | Use `/command [command name]` for more details.")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/1234567890/thumbnail_image.png")
    await ctx.send(embed=embed)

@bot.tree.command(name="command", description="Get detailed help for a specific command")
async def command_help_slash(interaction: discord.Interaction, command_name: str):
    command_name = command_name.lower()

    # Dictionary of commands with detailed descriptions
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
        "mute": "Mute a member so they can't send messages.",
        "unmute": "Unmute a member to allow them to send messages.",
        "giverole": "Give a role to a member.",
        "removerole": "Remove a role from a member.",
        "muteall": "Mute all members in the server.",
        "unmuteall": "Unmute all members in the server.",
        "lock": "Lock the current channel so no one can send messages.",
        "unlock": "Unlock the current channel to allow messages.",
        "lockdown": "Lock all channels in the server.",
        "stop_lockdown": "Unlock all channels in the server.",
        "afk": "Set yourself as AFK.",
        "unafk": "Remove your AFK status.",
        "roleinfo": "Get information about a specific role.",
        "invite": "Get the invite link for the bot.",
        "server_info": "Get information about the server.",
        "user_info": "Get information about a specific user.",
        "poll": "Create a poll to ask the server a question.",
        "remindme": "Set a reminder that notifies you at a specified time.",
        "servericon": "Get the server's icon.",
        "suggestion": "Submit a suggestion for the bot or server.",
        "staff_feedback": "Submit feedback for a staff member.",
        "events": "View upcoming events.",
        "event": "Create an event.",
        "shutdown": "Shut down the bot (OWNER ONLY).",
        "clear_all_warnings": "Clear all warnings for a member.",
        "nickname": "Change a user's nickname.",
        "warn": "Warn a member for breaking the rules.",
        "warnings": "View all warnings for a member.",
        "unwarn": "Remove a specific warning from a member.",
        "staff_suggestion": "Submit a suggestion only visible to staff.",
        "mod_panel": "Open a panel with moderator tools.",
        "report": "Report a user to the moderation team.",
        "setreportticket": "Send the In-Game Report ticket buttons.",
        "settickets": "Send support ticket buttons for various topics.",
        "up_time": "Show how long the bot has been running.",
        "dm": "Send yourself a DM with embed/message builder tools.",
        "session vote": "Start a vote for an ER:LC session action.",
    }

    # Try to match the command name
    matching = [name for name in command_details if command_name in name]

    if len(matching) == 1:
        cmd = matching[0]
        embed = discord.Embed(
            title=f"Help: /{cmd}",
            description=command_details[cmd],
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    elif len(matching) > 1:
        await interaction.response.send_message(
            f"Multiple matches found: {', '.join(matching)}. Please be more specific."
        )
    else:
        await interaction.response.send_message(
            f"Sorry, no detailed information found for `/command {command_name}`."
        )

# prefix command for detailed help
@bot.command(name="command", description="Get detailed help for a specific command")
async def command_help_prefix(ctx, command_name: str):
    command_name = command_name.lower()

    # Dictionary of commands with detailed descriptions
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
        "mute": "Mute a member so they can't send messages.",
        "unmute": "Unmute a member to allow them to send messages.",
        "giverole": "Give a role to a member.",
        "removerole": "Remove a role from a member.",
        "muteall": "Mute all members in the server.",
        "unmuteall": "Unmute all members in the server.",
        "lock": "Lock the current channel so no one can send messages.",
        "unlock": "Unlock the current channel to allow messages.",
        "lockdown": "Lock all channels in the server.",
        "stop_lockdown": "Unlock all channels in the server.",
        "afk": "Set yourself as AFK.",
        "unafk": "Remove your AFK status.",
        "roleinfo": "Get information about a specific role.",
        "invite": "Get the invite link for the bot.",
        "server_info": "Get information about the server.",
        "user_info": "Get information about a specific user.",
        "poll": "Create a poll to ask the server a question.",
        "remindme": "Set a reminder that notifies you at a specified time.",
        "servericon": "Get the server's icon.",
        "suggestion": "Submit a suggestion for the bot or server.",
        "staff_feedback": "Submit feedback for a staff member.",
        "events": "View upcoming events.",
        "event": "Create an event.",
        "shutdown": "Shut down the bot (OWNER ONLY).",
        "clear_all_warnings": "Clear all warnings for a member.",
        "nickname": "Change a user's nickname.",
        "warn": "Warn a member for breaking the rules.",
        "warnings": "View all warnings for a member.",
        "unwarn": "Remove a specific warning from a member.",
        "staff_suggestion": "Submit a suggestion only visible to staff.",
        "mod_panel": "Open a panel with moderator tools.",
        "report": "Report a user to the moderation team.",
        "setreportticket": "Send the In-Game Report ticket buttons.",
        "settickets": "Send support ticket buttons for various topics.",
        "up_time": "Show how long the bot has been running.",
        "dm": "Send yourself a DM with embed/message builder tools.",
        "session vote": "Start a vote for an ER:LC session action.",
    }
    # Try to match the command name
    matching = [name for name in command_details if command_name in name]
    if len(matching) == 1:
        cmd = matching[0]
        embed = discord.Embed(
            title=f"Help: /{cmd}",
            description=command_details[cmd],
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    elif len(matching) > 1:
        await ctx.send(f"Multiple matches found: {', '.join(matching)}. Please be more specific.")
    else:
        await ctx.send(f"Sorry, no detailed information found for `/command {command_name}`.")







from flask import Flask, render_template_string
import aiohttp
import asyncio
import nest_asyncio
import os

nest_asyncio.apply()

app = Flask(__name__)

HEADERS = {"server-key": API_KEY, "Accept": "application/json"}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SWAT Roleplay Community - ER:LC Server Info</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    body {
        background: #1f1f2e;
        color: #eee;
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 0;
    }
    .container {
        max-width: 900px;
        margin: 40px auto;
        padding: 25px;
        background: #2c2c44;
        border-radius: 15px;
        box-shadow: 0 0 25px #F39C12AA;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 15px;
    }
    .logo-container img {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        box-shadow: 0 0 15px #F39C12AA;
        border: 3px solid #F39C12;
        object-fit: cover;
    }
    h1 {
        text-align: center;
        margin-bottom: 30px;
        font-weight: 700;
        color: #F39C12;
        text-shadow: 0 0 5px #F39C12;
    }
    .stats {
        display: flex;
        justify-content: space-around;
        margin-bottom: 30px;
        flex-wrap: wrap;
        gap: 15px;
    }
    .stat-card {
        background: #3a3a5c;
        padding: 15px 25px;
        border-radius: 12px;
        text-align: center;
        flex: 1 1 120px;
        box-shadow: 0 0 15px #F39C12AA;
        transition: background 0.3s ease;
    }
    .stat-card:hover {
        background: #4a4a7c;
    }
    .stat-card h2 {
        margin: 0 0 10px 0;
        font-size: 22px;
        color: #f5b041;
    }
    .stat-card p {
        font-size: 18px;
        margin: 0;
    }
    .players-section {
        background: #3a3a5c;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 0 15px #F39C12AA;
        max-height: 350px;
        overflow-y: auto;
    }
    .players-section h2 {
        margin-top: 0;
        margin-bottom: 15px;
        color: #f5b041;
        text-align: center;
        font-weight: 700;
    }
    ul.player-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    ul.player-list li {
        padding: 8px 12px;
        border-bottom: 1px solid #4a4a7c;
        font-weight: 500;
        font-size: 16px;
        color: #ddd;
    }
    ul.player-list li:last-child {
        border-bottom: none;
    }
    footer {
        text-align: center;
        padding: 15px 0;
        color: #999;
        font-size: 14px;
        margin-top: 40px;
        user-select: none;
    }
</style>
</head>
<body>
<div class="container">
    <div class="logo-container">
        <img src="https://images-ext-1.discordapp.net/external/PiBV5Gc1y0XGSrS_xKZZTDTsFSHbYj7JNmZ7_30paYA/%3Fsize%3D1024/https/cdn.discordapp.com/icons/1343179590247645205/84d0898fb6fc8d1b07811e7b179629b4.png?format=webp&quality=lossless&width=625&height=625" alt="SWAT Roleplay Logo" />
    </div>
    <h1>SWAT Roleplay Community</h1>
    <div class="stats">
        <div class="stat-card">
            <h2>Players In-Game</h2>
            <p id="players_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Queue Count</h2>
            <p id="queue_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Staff In-Game</h2>
            <p id="staff_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Owner In-Game</h2>
            <p id="owner_status">Loading...</p>
        </div>
    </div>
    <div class="players-section">
        <h2>Players List</h2>
        <ul class="player-list" id="players_list">
            <li>Loading...</li>
        </ul>
    </div>
</div>
<footer>SWAT Roleplay Community</footer>

<script>
async function fetchData() {
    try {
        const response = await fetch('/data');
        const data = await response.json();

        document.getElementById('players_count').textContent = data.players_count;
        document.getElementById('queue_count').textContent = data.queue_count;
        document.getElementById('staff_count').textContent = data.staff_in_game_count;
        document.getElementById('owner_status').textContent = data.owner_in_game ? "Yes" : "No";

        const playersList = document.getElementById('players_list');
        playersList.innerHTML = '';

        if (data.players.length === 0) {
            playersList.innerHTML = '<li>No players online</li>';
        } else {
            for (const p of data.players) {
                const li = document.createElement('li');
                li.textContent = p;
                playersList.appendChild(li);
            }
        }
    } catch (err) {
        console.error('Error fetching data:', err);
        document.getElementById('players_count').textContent = 'Error';
        document.getElementById('queue_count').textContent = 'Error';
        document.getElementById('staff_count').textContent = 'Error';
        document.getElementById('owner_status').textContent = 'Error';
        document.getElementById('players_list').innerHTML = '<li>Error loading players</li>';
    }
}

// Initial fetch
fetchData();

// Refresh every 10 seconds
setInterval(fetchData, 10000);
</script>
</body>
</html>
"""

async def fetch_api(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            return None

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/data")
def get_data():
    # This function uses asyncio run to run async code inside Flask sync route.
    # If you run into issues, consider using Quart or a proper async framework.
    return asyncio.run(fetch_data())

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        # Fetch server info
        server_info = await fetch_api(session, "https://api.policeroleplay.community/v1/server")
        if not server_info:
            return {
                "players_count": "N/A",
                "queue_count": "N/A",
                "staff_in_game_count": "N/A",
                "owner_in_game": False,
                "players": []
            }

        # Fetch players
        players_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/players")
        if not players_data:
            players_data = []

        # Fetch queue
        queue_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/queue")
        if not queue_data:
            queue_data = []

        # Fetch staff list
        staff_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/staff")
        if not staff_data:
            staff_data = {}

        # Process counts
        players_count = len(players_data)
        queue_count = len(queue_data)

        # Determine staff IDs
        admins = staff_data.get("Admins", {})
        mods = staff_data.get("Mods", {})
        coowners = staff_data.get("CoOwners", [])

        staff_ids = set()
        # All staff IDs are keys in Admins and Mods (strings), and CoOwners is list of ints
        for k in admins.keys():
            try:
                staff_ids.add(int(k))
            except:
                pass
        for k in mods.keys():
            try:
                staff_ids.add(int(k))
            except:
                pass
        for co in coowners:
            try:
                staff_ids.add(int(co))
            except:
                pass

        # Count staff currently in game
        staff_in_game_count = 0
        owner_in_game = False
        players_list = []

        for player in players_data:
            # Player format: "PlayerName:Id"
            pname_id = player.get("Player", "")
            if ":" not in pname_id:
                continue
            pname, pid = pname_id.split(":")
            try:
                pid_int = int(pid)
            except:
                pid_int = None

            players_list.append(pname)

            if pid_int in staff_ids:
                staff_in_game_count += 1
            if pid_int == server_info.get("OwnerId"):
                owner_in_game = True

        return {
            "players_count": players_count,
            "queue_count": queue_count,
            "staff_in_game_count": staff_in_game_count,
            "owner_in_game": owner_in_game,
            "players": players_list
        }

if __name__ == "__main__":
    app.run(debug=True, port=5000)


bot.run((os.getenv("DISCORD_TOKEN")))  # Ensure you have your bot token set in the environment variable DISCORD_TOKEN
