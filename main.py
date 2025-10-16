# ========================= Import =========================

import discord
import random
import string
import datetime
import traceback
import json
from typing import Optional
import asyncio
import requests
import sys
import subprocess
import os
import logging
from discord import Embed
import re
import time
from datetime import datetime, timezone, timedelta
from datetime import datetime, timezone
from collections import defaultdict, deque
from discord.ext import commands, tasks
from discord import app_commands, ui
from discord.ui import View, Button, Select
from discord.utils import get
from discord.raw_models import RawReactionActionEvent
import aiohttp
from threading import Thread
import typing
import atexit
import copy
from dotenv import load_dotenv
import io
from typing import Union
import shutil
import urllib.parse

# ========================= Helpers =========================

COMMAND_PREFIX = "." # Prefix for commands
BOT_VERSION = "v1.0.3" # version
seen_players = set()  # Tracks players to avoid duplicate logs
last_joinleave_ts = 0 # Timestamp of last processed join/leave log think i fogot
# WELCOME_MESSAGE = "Welcome, please join the comms 8hVTv2wPCu, that's all. (bata)"
WELCOME_MESSAGE = "bata"

# ========================= On/Off =========================

welcome_status = True  # True = on, False = off
erlc_welcome_status = True  # True = on, False = off
DEBUG = False  # toggle debug logs

# ========================= Other =========================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log = logging.getLogger(__name__)

UTC = timezone.utc

SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blue()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True

kill_tracker = defaultdict(lambda: deque())

class MyBot(commands.Bot):
    async def setup_hook(self):
        global session
        session = aiohttp.ClientSession()
        print("✅ aiohttp session started")

    async def close(self):
        global session
        if session and not session.closed:
            await session.close()
            print("✅ aiohttp session closed")
        await super().close()

bot = MyBot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
tree = bot.tree
events = []

OWNER_ID = 1276264248095412387

session: aiohttp.ClientSession | None = None

erlc_group = app_commands.Group(name="erlc", description="ERLC related commands")
discord_group = app_commands.Group(name="discord", description="Discord-related commands")
staff_group = app_commands.Group(name="staff", description="Staff-only commands")
roblox_group = app_commands.Group(name="roblox", description="Roblox-related commands")

# ========================= Bot on_ready =========================

session: aiohttp.ClientSession | None = None  # global session

@bot.event
async def on_ready():
    # --------------------------------------------
    # Declare global variables to be used/modified
    # --------------------------------------------
    global session, seen_players, erlc_welcome_status, join_leave_status, last_joinleave_ts

    # ⚡ Debug: Bot is starting up
    print("⚡ Bot starting...")

    # --------------------------------------------
    # Initialize global variables if they don't exist
    # --------------------------------------------
    if 'seen_players' not in globals():
        # Set to keep track of players we have already seen in join logs
        seen_players = set()
    if 'erlc_welcome_status' not in globals():
        # Boolean flag to enable/disable ER:LC welcome messages
        erlc_welcome_status = False
    if 'join_leave_status' not in globals():
        # Boolean flag to control join/leave logging
        join_leave_status = False
    if 'last_joinleave_ts' not in globals():
        # Timestamp of the latest join/leave log processed
        last_joinleave_ts = 0

    # --------------------------------------------
    # Register slash command groups
    # --------------------------------------------
    try:
        # Add command groups to bot's command tree
        bot.tree.add_command(erlc_group)
        bot.tree.add_command(discord_group)
        bot.tree.add_command(staff_group)
        bot.tree.add_command(roblox_group)

        # Sync commands globally
        await bot.tree.sync()
        print("✅ Slash commands synced!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    # --------------------------------------------
    # Set bot startup time
    # --------------------------------------------
    bot.start_time = datetime.now(timezone.utc)  # timezone-aware UTC time
    print(f"Bot start time set to {bot.start_time.isoformat()}")

    # --------------------------------------------
    # Initialize aiohttp session if not already open
    # --------------------------------------------
    if session is None or session.closed:
        # aiohttp session used for API requests
        session = aiohttp.ClientSession()
        print("✅ aiohttp session started")

    # --------------------------------------------
    # Initialize seen players from ER:LC join logs
    # --------------------------------------------
    try:
        # Fetch join logs from API
        joinlogs = await fetch_joinlogs()
        max_ts = 0  # Track the latest timestamp

        # Loop through all join log entries
        for entry in joinlogs:
            ts = entry.get("Timestamp", 0)  # Timestamp of this log
            player = entry.get("Player")    # Player string (username:ID)

            # Only add players who joined to the seen_players set
            if player and entry.get("Join"):
                seen_players.add(player)

            # Update max timestamp seen
            if ts > max_ts:
                max_ts = ts

        # Set last_joinleave_ts to latest timestamp to ignore old logs
        last_joinleave_ts = max_ts
        print(f"✅ Initialized seen_players with {len(seen_players)} entries, last_joinleave_ts={last_joinleave_ts}")

    except Exception as e:
        # Handle errors fetching join logs
        print(f"⚠️ Failed to initialize seen_players: {e}")

    # --------------------------------------------
    # Start all background tasks
    # --------------------------------------------
    try:
        # Tasks for logging joins/leaves, kills, mod calls, etc.
        join_leave_log_erlc_welcome_message_task.start()        # Logs new join/leave events # Sends ER:LC welcome messages
        kill_log_task.start()              # Logs kill events
        modcall_log_task.start()           # Logs moderator calls
        team_join_leave_log_task.start()   # Logs team join/leave events
        update_vc_status.start()           # Updates VC status regularly
        discord_check_task.start()         # Checks for Discord related events         
        update_member_count_vcs.start()   # Updates member count in VCs
        print("✅ Background tasks started")
    except Exception as e:
        print(f"⚠️ Error starting background tasks: {e}")

    # --------------------------------------------
    # Start presence updater task
    # --------------------------------------------
    update_presence.start()
    print("✅ Presence updater started")


    # --------------------------------------------
    # Final debug info: bot is fully connected
    # --------------------------------------------
    print(f"{bot.user} ({bot.user.id}) has connected to Discord and is monitoring the server.")
    print("-----------------------------------------------------------------------")


# ---------------------- Presence Loop ----------------------
@tasks.loop(seconds=300)  # Update every 5 minutes
async def update_presence():
    """Loop through presence messages periodically."""
    statuses = [
        "over the server",
        ".commands",
        "your safety",
        "the logs",
        "SRPC Operations"
    ]

    for status_text in statuses:
        # print(f"[DEBUG] Setting presence: Watching {status_text}")
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=status_text
            ),
        )
        await asyncio.sleep(20)  # Wait 20 seconds before changing again

# ========================= Emojis =========================

time_emoji = "<:time:1387841153491271770>"
tick_emoji = "<:tick:1383796116763709532>"
error_emoji = "<:error:1417568252355280946>"
ping_emoji = "<:ping:1417568793546326057>"
logo_emoji = "<:logo:1322987575375429662>"
pong_emoji = "<:pong:1387845465315348480>"
failed_emoji = "<:failed:1387853598733369435>"
note_emoji = "<:note:1387865341773873302>"
clipboard_emoji = "<:clipboard:1387890654868410408>"
owner_emoji = "<:owner:1387900933006164160>"
bypass_emoji = "<:bypass:1417555104789172375>"
dot_emoji = "<:dot:1411743202142191786>"
L_emoji = "<:lL:1411743187906723930>"
help_emoji = "<:help:1411741689785352264>"
an_emoji = "<:an:1411741518187991170>"
staff_emoji = "<:staff:1410776282920259715>"
people_emoji = "<:people:1417569841514283133>"

# ========================= IDs =========================

# ---------------------- STAFF ROLES ----------------------

staff_role_id = 1343234687505530902
mod_role_id = 1346576470360850432
admin_role_id = 1346577013774880892
superviser_role_id = 1346577369091145728
management_role_id = 1346578020747575368
ia_role_id = 1371537163522543647
ownership_role_id = 1346578250381656124

# ---------------------- OTHER STAFF ROLES ----------------------

session_manager_role_id = 1374839922976100472
staff_trainer_role_id = 1377794070440837160
event_Coordinator_role_id = 1346740470272757760
staff_help_role_id = 1370096425282830437
staff_blacklist_role_id = 1350831407500628049
partnership_role_id = 1346740305746989056

# ---------------------- OTHER ROLES ----------------------

afk_role_id = 1355829296085729454
session_ping_role_id = 1343487514358583347

# ---------------------- USER IDS ----------------------

owner_id = 1276264248095412387
dj_id = 1296842183344918570

# ========================= IS A ROLE CALLS =========================

def is_staff(): return app_commands.check(lambda i: i.guild and any(r.id == staff_role_id for r in i.user.roles))
def is_mod(): return app_commands.check(lambda i: i.guild and any(r.id == mod_role_id for r in i.user.roles))
def is_admin(): return app_commands.check(lambda i: i.guild and any(r.id == admin_role_id for r in i.user.roles))
def is_superviser(): return app_commands.check(lambda i: i.guild and any(r.id == superviser_role_id for r in i.user.roles))
def is_management(): return app_commands.check(lambda i: i.guild and any(r.id == management_role_id for r in i.user.roles))
def is_ia(): return app_commands.check(lambda i: i.guild and any(r.id == ia_role_id for r in i.user.roles))
def is_ownership(): return app_commands.check(lambda i: i.guild and any(r.id == ownership_role_id for r in i.user.roles))

# ---------------------- OTHER STAFF ROLES ----------------------

def is_session_manager(): return app_commands.check(lambda i: i.guild and any(r.id == session_manager_role_id for r in i.user.roles))
def is_staff_trainer(): return app_commands.check(lambda i: i.guild and any(r.id == staff_trainer_role_id for r in i.user.roles))
def is_event_coordinator(): return app_commands.check(lambda i: i.guild and any(r.id == event_Coordinator_role_id for r in i.user.roles))
def is_staff_help(): return app_commands.check(lambda i: i.guild and any(r.id == staff_help_role_id for r in i.user.roles))
def is_staff_blacklist(): return app_commands.check(lambda i: i.guild and any(r.id == staff_blacklist_role_id for r in i.user.roles))

# ---------------------- USER ----------------------

def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == owner_id
    return app_commands.check(predicate)

# --- Helper Function for Uptime ---
def get_uptime(bot) -> str:
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

    return ", ".join(uptime_parts)


# ========================= COMMANDS =========================

# ---------------------- .PING ----------------------

# Helper function to create the ping embed
def create_ping_embed(ctx_or_interaction):
    latency = round(bot.latency * 1000)
    uptime_str = get_uptime(bot)
    embed = discord.Embed(
        title=f"{pong_emoji} Pong!",
        description=(
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"> Version: `{BOT_VERSION}`\n"
        ),
        color=0x1E77BE
    )
    
    # Determine whether it's a Context (prefix command) or Interaction (slash command)
    if isinstance(ctx_or_interaction, commands.Context):
        embed.set_author(name=ctx_or_interaction.guild.name, icon_url=ctx_or_interaction.guild.icon.url)
    else:  # discord.Interaction
        embed.set_author(name=ctx_or_interaction.guild.name, icon_url=ctx_or_interaction.guild.icon.url)
    
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

# Prefix command
@bot.command(name="ping")
async def ping_prefix(ctx: commands.Context):
    embed = create_ping_embed(ctx)
    await ctx.send(embed=embed)

# Slash command
@bot.tree.command(name="ping", description="Check the bot's latency and uptime")
async def ping_slash(interaction: discord.Interaction):
    embed = create_ping_embed(interaction)
    await interaction.response.send_message(embed=embed)

# ---------------------- .uptime ----------------------

@bot.command(name="uptime")
async def uptime_prefix(ctx: commands.Context):
    uptime_str = get_uptime(bot)

    embed = discord.Embed(
        title=f"{time_emoji} Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=0x1E77BE
    )

    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await ctx.send(embed=embed)

# ---------------------- /uptime ----------------------

@bot.tree.command(name="uptime", description="Check how long the bot has been online")
async def uptime_slash(interaction: discord.Interaction):
    uptime_str = get_uptime(bot)

    embed = discord.Embed(
        title=f"{time_emoji} Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=0x1E77BE
    )

    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await interaction.response.send_message(embed=embed)

# ---------------------- .servers ----------------------

# Helper function to create server embed
async def create_guild_embed(guild: discord.Guild):
    owner = guild.owner
    invite_link = "No invite available"

    # Try to create an invite for the first available text channel
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).create_instant_invite:
            try:
                invite = await channel.create_invite(max_age=3600, max_uses=1, unique=True)
                invite_link = invite.url
                break
            except (discord.errors.Forbidden, discord.errors.HTTPException) as e:
                print(f"Failed to create invite for guild '{guild.name}': {e}")
                # Keep invite_link as "No invite available"

    embed = discord.Embed(
        title=guild.name,
        description=(
            f"ID: `{guild.id}`\n"
            f"Owner: {owner}\n"
            f"Members: {guild.member_count}\n"
            f"Invite: {invite_link}"
        ),
        color=0x1E77BE
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

# Prefix command
@bot.command(name="servers")
@commands.is_owner()
async def servers_prefix(ctx: commands.Context):
    await ctx.defer()
    guilds = bot.guilds
    if not guilds:
        await ctx.send("The bot is not in any servers.")
        return

    for guild in guilds:
        embed = await create_guild_embed(guild)
        await ctx.send(embed=embed)

# Slash command
@bot.tree.command(name="servers", description="List all servers the bot is in")
@is_owner()
async def servers_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guilds = bot.guilds
    if not guilds:
        await interaction.followup.send("The bot is not in any servers.")
        return

    for guild in guilds:
        embed = await create_guild_embed(guild)
        await interaction.followup.send(embed=embed, ephemeral=True)


# ---------------------- .sync ----------------------

# --------------------------
# Embeds for Sync Command
# --------------------------
def synced_embed(ctx: commands.Context, synced_count: int):
    """Embed for successful sync"""
    embed = discord.Embed(
        title=f"{tick_emoji_2} Commands Synced",
        description=f"{tick_emoji_2} Synced **{synced_count}** application command(s).",
        color=0x1E77BE
    )
    if ctx.guild:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed


def failed_embed(ctx: commands.Context, error_msg: str):
    """Embed for failed sync"""
    embed = discord.Embed(
        title=f"{failed_emoji_2} Sync Failed",
        description=f"{failed_emoji_2} Failed to sync commands:\n```{error_msg}```",
        color=discord.Color.red()
    )
    if ctx.guild:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

# --------------------------
# Sync Command
# --------------------------
@bot.command(name="sync")
async def sync(ctx: commands.Context):
    """Owner-only command: .sync"""
    if ctx.author.id != OWNER_ID:
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.HTTPException as e:
            print(f"[WARN] Failed to react with failed_emoji: {e}")
        return await ctx.send(
            embed=discord.Embed(
                title="🚫 Access Denied",
                description="Only the bot owner can run this command.",
                color=discord.Color.red()
            )
        )

    try:
        async with ctx.typing():
            synced = await ctx.bot.tree.sync()
        count = len(synced)

        try:
            await ctx.message.add_reaction(tick_emoji_2)
        except discord.HTTPException as e:
            print(f"[WARN] Failed to react with tick_emoji: {e}")

        await ctx.send(embed=synced_embed(ctx, count))

    except Exception as e:
        try:
            await ctx.message.add_reaction(failed_emoji_2)
        except discord.HTTPException:
            pass

        await ctx.send(embed=failed_embed(ctx, str(e)))
        print(f"[ERROR] !sync failed: {e}")

# --

# make restarting embed
def restart_embed(ctx: commands.Context):
    """Embed for restarting the bot"""
    embed = discord.Embed(
        title=f"{ping_emoji} Restarting Bot",
        description="♻️ The bot is restarting...",
        color=0x1E77BE
    )
    if ctx.guild:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

# make fail embed
def fail_embed(ctx: commands.Context, error_msg: str):
    """Embed for failed restart"""
    embed = discord.Embed(
        title=f"{failed_emoji_2} Restart Failed",
        description=f"{failed_emoji_2} Failed to restart the bot:\n```{error_msg}```",
        color=discord.Color.red()
    )
    if ctx.guild:
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

@bot.command(name="restart")
async def restart(ctx):
    """Owner-only: restart the bot"""
    if ctx.author.id != OWNER_ID:
        # react with failed emoji for non-owner
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.HTTPException as e:
            log.warning("Failed to react with failed_emoji: %s", e)
        return

    # react with tick emoji for owner
    try:
        await ctx.message.add_reaction(tick_emoji)
    except discord.HTTPException as e:
        log.warning("Failed to react with tick_emoji: %s", e)

    await ctx.send(embed=restart_embed(ctx))

    # --- Validate python executable (avoid untrusted paths) ---
    python_path = sys.executable  # usually an absolute path

    # If sys.executable is missing or not executable, try finding python via PATH
    if not (python_path and os.path.isabs(python_path) and os.access(python_path, os.X_OK)):
        python_path = shutil.which("python3") or shutil.which("python")

    if not python_path:
        # Fail early with clear message rather than blindly invoking execv
        await ctx.send(embed=fail_embed(ctx, "Could not locate a valid Python executable to restart the bot."))
        log.error("Restart failed: could not locate python executable (sys.executable=%r)", sys.executable)
        return

    # Build safe argv list (do not use shell)
    argv = [python_path] + sys.argv

    # Close bot cleanly, then replace current process image with the new one
    try:
        await bot.close()
    except Exception as e:
        # We still attempt execv even if close had issues, but log the problem.
        log.exception("Error while closing bot before restart: %s", e)

    # Exec the new interpreter. This does not invoke a shell and uses absolute path.
    # This is intentional and safe.  # nosec: B606
    try:
        os.execv(python_path, argv)  # nosec: B606
    except OSError as e:
        # Exec failed — inform operator and log full traceback
        await ctx.send(embed=fail_embed(ctx, f"os.execv failed: {e}"))
        log.exception("os.execv failed while attempting to restart: %s", e)

# ========================= ERLC stuff =========================

# ---------------------- ERLC setup ----------------------

ROBLOX_USER_API = "https://users.roblox.com/v1/users"
JOIN_LEAVE_LOG_CHANNEL_ID = 1382852078048907274
KILL_LOG_CHANNEL_ID = 1382852078048907274
MODCALL_LOG_CHANNEL_ID = 1382852078048907274
TEAM_JOIN_LEAVE_LOG_CHANNEL_ID = 1382852078048907274
COMMAND_LOG_CHANNEL_ID = 1382852078048907274
 
API_KEY = os.getenv("API_KEY")
API_BASE = os.getenv("API_BASE")

# === API HEADERS ===
HEADERS_GET = {
    "server-key": API_KEY,
    "Accept": "*/*"
}
HEADERS_POST = {
    "server-key": API_KEY,
    "Content-Type": "application/json"
}

# ---------------------- join/leave logs / erlc welcome message ----------------------

# --- Helper Functions ---
async def fetch_joinlogs():
    url = "https://api.policeroleplay.community/v1/server/joinlogs"
    headers = {"server-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"[DEBUG] Failed to fetch join logs: {resp.status}")
                return []
            data = await resp.json()
            return data

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG {datetime.now(timezone.utc)}] {msg}")

def parse_player(player_str):
    """Return (username, player_id)"""
    try:
        username, id_str = player_str.split(":", 1)
        return username, int(id_str)
    except (ValueError, AttributeError):
        return player_str, 0

def format_player_link(username, player_id):
    """Return markdown link to Roblox profile"""
    return f"[{username}](https://www.roblox.com/users/{player_id}/profile)" if player_id else username

def process_join_leave(entry, seen_players):
    """Return timestamp, join_event, leave_event"""
    ts = entry.get("Timestamp", 0)
    player_str = entry.get("Player", "Unknown:0")
    joined = entry.get("Join", True)

    username, player_id = parse_player(player_str)
    user_link = format_player_link(username, player_id)

    join_event, leave_event = None, None

    if joined:
        if player_str not in seen_players:
            join_event = f"{user_link} joined at <t:{ts}:F>"
            seen_players.add(player_str)
            debug_print(f"Player joined: {player_str}")
    else:
        if player_str in seen_players:
            leave_event = f"{user_link} left at <t:{ts}:F>"
            seen_players.remove(player_str)
            debug_print(f"Player left: {player_str}")

    return ts, join_event, leave_event

async def send_joinleave_log_embed(channel, title, events, color=0x1E77BE):
    """Sends formatted embed to Discord channel"""
    if not events:
        debug_print(f"No events to send for '{title}'")
        return

    embed = discord.Embed(
        title=title,
        description="\n".join(events),
        colour=color
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await channel.send(embed=embed)
    debug_print(f"Sent '{title}' embed with {len(events)} events")

async def send_welcome_pm(username):
    """Send PM in-game via API"""
    # Replace with your actual in-game PM wrapper
    await send_to_game(f":pm {username} {WELCOME_MESSAGE}")

# -------------------------------
# BACKGROUND TASK
# -------------------------------

@tasks.loop(seconds=60)
async def join_leave_log_erlc_welcome_message_task():
    global session, last_joinleave_ts, seen_players

    # Start session if missing
    if not session or session.closed:
        session = aiohttp.ClientSession()
        debug_print("Started new aiohttp session")

    # Fetch join logs
    try:
        async with session.get(f"{API_BASE}/joinlogs", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
                debug_print(f"Failed to fetch join logs: {resp.status}")
                return
            data = await resp.json()
            debug_print(f"Fetched {len(data)} join log entries")
    except Exception as e:
        debug_print(f"Exception fetching join logs: {e}")
        return

    if not data:
        debug_print("No join logs returned")
        return

    # Fetch Discord channel
    channel = bot.get_channel(JOIN_LEAVE_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(JOIN_LEAVE_LOG_CHANNEL_ID)
        except Exception as e:
            debug_print(f"Failed to fetch join/leave log channel: {e}")
            return

    join_events, leave_events = [], []
    max_ts = last_joinleave_ts

    # Process each entry
    for entry in data:
        ts, join_event, leave_event = process_join_leave(entry, seen_players)
        if ts <= last_joinleave_ts:
            continue
        if join_event:
            join_events.append(join_event)
            if erlc_welcome_status:
                username = entry.get("Player", "").split(":")[0]
                await send_welcome_pm(username)
        if leave_event:
            leave_events.append(leave_event)
        max_ts = max(max_ts, ts)

    last_joinleave_ts = max_ts

    # Send embeds
    if join_events:
        await send_joinleave_log_embed(channel, "Join Log", join_events, 0x00f529)
    if leave_events:
        await asyncio.sleep(5)  # Small delay
        await send_joinleave_log_embed(channel, "Leave Log", leave_events, 0xf50000)

# -

# --------------------------------------------
# Helper Function: Format Kill Entry
# --------------------------------------------
def format_kill_entry(entry: dict) -> str:
    """Formats a raw kill log entry into a readable Discord message."""
    ts = entry.get("Timestamp", 0)
    killer_raw = entry.get("Killer", "Unknown:0")
    victim_raw = entry.get("Killed", "Unknown:0")

    # Split "Username:UserId"
    if ":" in killer_raw:
        killer_name, killer_id = killer_raw.split(":", 1)
    else:
        killer_name, killer_id = killer_raw, "0"

    if ":" in victim_raw:
        victim_name, victim_id = victim_raw.split(":", 1)
    else:
        victim_name, victim_id = victim_raw, "0"

    # Build Roblox profile links if IDs are valid
    killer_link = f"[{killer_name}](https://www.roblox.com/users/{killer_id}/profile)" if killer_id != "0" else killer_name
    victim_link = f"[{victim_name}](https://www.roblox.com/users/{victim_id}/profile)" if victim_id != "0" else victim_name

    return f"{killer_link} killed {victim_link} at <t:{ts}:F>"


# --------------------------------------------
# Background Task: Check ER:LC Kill Logs
# --------------------------------------------
@tasks.loop(seconds=120)
async def kill_log_task():
    """Polls the ER:LC kill logs API and sends updates to Discord."""
    global session

    if not session or session.closed:
        session = aiohttp.ClientSession()
     #   print("[DEBUG] aiohttp session started in kill_log_task")

 #   print("[DEBUG] kill_log_task running...")

    # Fetch kill logs from API
    try:
        async with session.get(f"{API_BASE}/killlogs", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
               # print(f"[DEBUG] Failed to fetch kill logs: {resp.status}")
                return
            data = await resp.json()
        #    print(f"[DEBUG] Fetched {len(data)} kill log entries")
    except Exception as e:
    #    print(f"[DEBUG] Exception fetching kill logs: {e}")
        return

    if not data:
    #    print("[DEBUG] No kill logs returned")
        return

    # Get channel
    channel = bot.get_channel(KILL_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(KILL_LOG_CHANNEL_ID)
        except Exception as e:
           # print(f"[DEBUG] Failed to fetch kill log channel: {e}")
            return

    # Initialize timestamp tracker on first run
    if not hasattr(kill_log_task, "last_ts"):
        # ⛔ Skip sending old logs from before bot start
        kill_log_task.last_ts = max(entry.get("Timestamp", 0) for entry in data)
     #   print(f"[DEBUG] Initialized kill_log_task.last_ts = {kill_log_task.last_ts} (skipping old logs)")
        return

    kill_events = []
    latest_ts = kill_log_task.last_ts

    for entry in data:
        ts = entry.get("Timestamp", 0)
        if ts <= kill_log_task.last_ts:
            continue  # Skip old logs
        kill_events.append(format_kill_entry(entry))
        latest_ts = max(latest_ts, ts)

    kill_log_task.last_ts = latest_ts  # Update last processed timestamp

    if not kill_events:
      #  print("[DEBUG] No new kill events since last check")
        return

    # Send embed
    embed = discord.Embed(
        title="Kill Log",
        description="\n".join(kill_events),
        colour=0xffa200
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await channel.send(embed=embed)

   # print(f"[DEBUG] Sent Kill Log embed with {len(kill_events)} new entries")

# ---------------------- mocall logs ----------------------

@tasks.loop(seconds=120)
async def modcall_log_task():
    global session

    # Ensure aiohttp session exists
    if not session or session.closed:
        session = aiohttp.ClientSession()
       # print("[DEBUG] aiohttp session started for modcall_log_task")

  #  print("[DEBUG] modcall_log_task running...")

    # Fetch modcall logs from ER:LC API
    try:
        async with session.get(f"{API_BASE}/modcalls", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
            #    print(f"[DEBUG] Failed to fetch modcall logs: {resp.status}")
                return
            data = await resp.json()
          #  print(f"[DEBUG] Fetched {len(data)} modcall log entries")
    except Exception as e:
   #     print(f"[DEBUG] Exception fetching modcall logs: {e}")
        return

    if not data:
       # print("[DEBUG] No modcall logs returned")
        return

    # Get or fetch the channel
    channel = bot.get_channel(MODCALL_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(MODCALL_LOG_CHANNEL_ID)
        except Exception as e:
        #    print(f"[DEBUG] Failed to fetch modcall log channel: {e}")
            return

    # Track last processed timestamp
    if not hasattr(modcall_log_task, "last_ts"):
        # Initialize to the latest log on startup — this prevents old logs from sending
        modcall_log_task.last_ts = max((int(e.get("Timestamp", 0)) for e in data), default=0)
       # print(f"[DEBUG] Initialized modcall_log_task.last_ts = {modcall_log_task.last_ts} (skipping old logs)")
        return  # Skip sending logs on first run

    modcall_events = []

    for entry in data:
        ts = int(entry.get("Timestamp", 0))
        if ts <= modcall_log_task.last_ts:
            continue

        # Parse Caller
        caller_raw = entry.get("Caller", "Unknown:0")
        try:
            caller_name, caller_id_str = caller_raw.split(":", 1)
            caller_id = int(caller_id_str)
        except (ValueError, AttributeError):
            caller_name, caller_id = caller_raw, 0

        # Parse Moderator (optional)
        moderator_raw = entry.get("Moderator")
        if moderator_raw:
            try:
                mod_name, mod_id_str = moderator_raw.split(":", 1)
                mod_id = int(mod_id_str)
            except (ValueError, AttributeError):
                mod_name, mod_id = moderator_raw, 0
        else:
            mod_name, mod_id = "Unassigned", 0

        # Build clickable links
        caller_link = (
            f"[{caller_name}](https://www.roblox.com/users/{caller_id}/profile)"
            if caller_id else caller_name
        )
        moderator_link = (
            f"[{mod_name}](https://www.roblox.com/users/{mod_id}/profile)"
            if mod_id else mod_name
        )

        # Build formatted event string
        modcall_events.append(f"{moderator_link} responded to {caller_link} at <t:{ts}:F>")
        modcall_log_task.last_ts = max(modcall_log_task.last_ts, ts)
      #  print(f"[DEBUG] Processed new modcall log: {moderator_link} -> {caller_link} at {ts}")

    # Send all new modcalls in one embed
    if modcall_events:
        embed = discord.Embed(
            title="Modcall Log",
            description="\n".join(modcall_events),
            colour=0xe1ff00
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await channel.send(embed=embed)
       # print(f"[DEBUG] Sent {len(modcall_events)} new modcall events")

# ---------------------- team join/leave logs ----------------------

@tasks.loop(seconds=80)
async def team_join_leave_log_task():
    global session

    # Ensure session exists
    if not session or session.closed:
        session = aiohttp.ClientSession()
     #   print("[DEBUG] aiohttp session started for team_join_leave_log_task")

 #   print("[DEBUG] team_join_leave_log_task running...")

    # Fetch players from API
    players = await fetch_players()
    if not players:
     #   print("[DEBUG] No players fetched, skipping.")
        return

    # Get the Discord channel
    channel = await get_team_log_channel()
    if not channel:
     #   print("[DEBUG] Failed to get team log channel, skipping.")
        return

    # On first run, initialize state and skip sending
    if not hasattr(team_join_leave_log_task, "last_team_state"):
        team_join_leave_log_task.last_team_state = {parse_player_id(p.get("Player", "Unknown:0"))[1]:
                                                    normalize_team_name(p.get("Team")) for p in players}
      #  print("[DEBUG] Initialized team state (skipping old team logs on startup)")
        return

    # Compute changes since last run
    join_events, leave_events = compute_team_changes(players, team_join_leave_log_task.last_team_state)

    # Combine and send logs (with delay to batch quick changes)
    if join_events or leave_events:
     #   print(f"[DEBUG] Found {len(join_events)} joins and {len(leave_events)} leaves.")
      #  print("[DEBUG] Waiting 10 seconds before sending team logs to allow batching...")
        

        # Re-check if new events appeared during delay (optional — can skip)
        # No re-fetch here to keep simple

        # Send batched logs
        await send_team_joinleave__log_embed(channel, "Team Leave Log", leave_events)
        await asyncio.sleep(10)  # delay to prevent spam when users switch fast
        await send_team_joinleave__log_embed(channel, "Team Join Log", join_events)
      #  print("[DEBUG] Sent team join/leave embeds.")
    else:
       # print("[DEBUG] No team changes detected.")
       pass


# --- Helper Functions ---

async def fetch_players():
    try:
        async with session.get(f"{API_BASE}/players", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
               # print(f"[DEBUG] Failed to fetch players: {resp.status}")
                return []
            data = await resp.json()
          #  print(f"[DEBUG] Fetched {len(data)} players")
            return data
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
      #  print(f"[DEBUG] Error fetching players: {e}")
        return []


async def get_team_log_channel():
    channel = bot.get_channel(TEAM_JOIN_LEAVE_LOG_CHANNEL_ID)
    if channel:
        return channel
    try:
        return await bot.fetch_channel(TEAM_JOIN_LEAVE_LOG_CHANNEL_ID)
    except discord.DiscordException as e:
     #   print(f"[DEBUG] Failed to fetch team log channel: {e}")
        return None


def compute_team_changes(players, last_team_state):
    join_events, leave_events = [], []
    ts = int(time.time())

    for player in players:
        username, player_id = parse_player_id(player.get("Player", "Unknown:0"))
        team_name = normalize_team_name(player.get("Team"))
        callsign = player.get("Callsign")
        previous_team = last_team_state.get(player_id)

        if previous_team != team_name:
            player_link = format_player_link(username, player_id)
            process_team_change(join_events, leave_events, previous_team, team_name, player_link, callsign, ts)

        last_team_state[player_id] = team_name

    return join_events, leave_events


def parse_player_id(player_raw):
    try:
        username, id_str = player_raw.split(":", 1)
        return username, int(id_str)
    except (ValueError, AttributeError):
        return player_raw, 0


def normalize_team_name(team_name):
    if not team_name or team_name.lower() == "none":
        return None
    return team_name


def format_player_link(username, player_id):
    if player_id:
        return f"[{username}](https://www.roblox.com/users/{player_id}/profile)"
    return username


def process_team_change(join_events, leave_events, previous_team, current_team, player_link, callsign, ts):
    if previous_team is None and current_team:
        # Joined a team
        text = f"{player_link} joined {current_team}"
        if callsign:
            text += f" ({callsign})"
        join_events.append(f"{text} at <t:{ts}:F>")
    elif previous_team and not current_team:
        # Left a team
        leave_events.append(f"{player_link} left {previous_team} at <t:{ts}:F>")
    elif previous_team and current_team and previous_team != current_team:
        # Switched teams
        leave_events.append(f"{player_link} left {previous_team} at <t:{ts}:F>")
        text = f"{player_link} joined {current_team}"
        if callsign:
            text += f" ({callsign})"
        join_events.append(f"{text} at <t:{ts}:F>")


async def send_team_joinleave__log_embed(channel, title, events):
    if not events:
        return
    embed = discord.Embed(
        title=title,
        description="\n".join(events),
        colour=0xffffff
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await channel.send(embed=embed)

# ---------------------- error code ----------------------

# --- Error message function ---
def get_erlc_error_message(http_status: int, api_code: int = None, exception: Exception = None) -> str:
    """
    Returns a formatted PRC error message with optional API code or exception details.
    Only includes the official error codes.
    """
    messages = {
        # HTTP errors
        400: f"{error_emoji} **400 – Bad Request**: The request was malformed or invalid.",
        403: f"{error_emoji} **403 – Unauthorized**: You do not have permission to access this resource.",
        422: f"{error_emoji} **422 – No Players**: The private server has no players in it.",

        # API codes
        0: "Unknown error occurred. If this is persistent, contact PRC via an API ticket.",
        1001: "An error occurred communicating with Roblox / the in-game private server.",
        1002: "An internal system error occurred.",
        2000: "You did not provide a server-key.",
        2001: "You provided an incorrectly formatted server-key.",
        2002: "You provided an invalid (or expired) server-key.",
        2003: "You provided an invalid global API key.",
        2004: "Your server-key is currently banned from accessing the API.",
        3001: "You did not provide a valid command in the request body.",
        3002: "The server you are attempting to reach is currently offline (has no players).",
        4001: "You are being rate limited.",
        4002: "The command you are attempting to run is restricted.",
        4003: "The message you're trying to send is prohibited.",
        9998: "The resource you are accessing is restricted.",
        9999: "The module running on the in-game server is out of date, please kick all and try again."
    }

    # If exception exists but status is 0, just show exception
    if http_status == 0 and exception:
        return f"{error_emoji} **Unhandled Exception**:\n`{str(exception)}`"

    base_message = messages.get(
        api_code if api_code is not None else http_status,
        f"{error_emoji} **{http_status} – Unknown Error**: An unexpected error occurred."
    )

    if exception:
        base_message += f"\n`{str(exception)}`"

    return base_message

# ---------------------- get roblox usernames ----------------------

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

# ---------------------- jon server button for erlc info embed ----------------------

class InfoView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, embed_callback):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.embed_callback = embed_callback

        # Join Server is added first
        self.add_item(discord.ui.Button(
            label="Join Server",
            style=discord.ButtonStyle.secondary,
            url="https://policeroleplay.community/join/SWATxRP"
        ))

# ---------------------- erlc info button ----------------------

async def erlc_info_embed(interaction: discord.Interaction) -> discord.Embed:
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
        color=0x1E77BE,
    )
    embed.add_field(
        name=f"{clipboard_emoji} Basic Info",
        value=(
            f"> **Server name:** {server['Name']}\n"
            f"> **Join Code:** [{server['JoinKey']}](https://policeroleplay.community/join/{server['JoinKey']})\n"
            f"> **Players:** {server['CurrentPlayers']}/{server['MaxPlayers']}\n"
            f"> **Queue:** {len(queue)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"{staff_emoji} Staff Info",
        value=(
            f"> **Moderators:** {len(mods)}\n"
            f"> **Administrators:** {len(admins)}\n"
            f"> **Staff in Server:** {len(staff)}\n"
            f"> **Owner:** [{usernames[owner_id]}](https://roblox.com/users/{owner_id}/profile)\n"
            f"> **Co-Owners:** {', '.join([f'[{usernames[uid]}](https://roblox.com/users/{uid}/profile)' for uid in co_owner_ids]) or 'None'}"
        ),
        inline=False
    )

    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")

    return embed

# ---------------------- /erlc info ----------------------

@erlc_group.command(name="info", description="Get ER:LC server info with live data.")
async def erlc_info(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        embed = await erlc_info_embed(interaction)
        view = InfoView(interaction, lambda: erlc_info_embed(interaction))
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        # Use the error handler for all errors
        error_message = get_erlc_error_message(0, exception=e)
        await interaction.followup.send(error_message)
        print(f"[ERROR] /erlc info failed: {e}")

# ---------------------- logging for /erlc command ----------------------

async def log_command(user: discord.User, command: str):
    channel = bot.get_channel(COMMAND_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(COMMAND_LOG_CHANNEL_ID)
        except Exception:
            return

    embed = discord.Embed(
        title="Command Usage Log",
        description=f"[{user}](https://discord.com/users/{user.id}) ran the command `{command}` at <t:{int(time.time())}:F>",
        colour=0x1E77BE
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await channel.send(embed=embed)

# ---------------------- perm check for /erlc command ----------------------

def allowed_to_run(user: discord.User, command: str, guild: discord.Guild) -> bool:
    """Check if a user is allowed to run a command."""
    if user.id == owner_id:
        return True

    if not guild:
        return False  # Cannot check roles outside a guild

    member = guild.get_member(user.id)
    if not member:
        return False

    roles = {r.id for r in member.roles}
    if mod_role_id in roles or admin_role_id in roles or ownership_role_id in roles:
        return True

    return False

# ---------------------- /erlc command ----------------------

@erlc_group.command(name="command", description="Run a command in the ERLC server")
async def erlc_command(interaction: discord.Interaction, command: str):
    global session
    if not session:
        session = aiohttp.ClientSession()

    user = interaction.user
    base_cmd = command.split()[0].lower()

    if not allowed_to_run(user, base_cmd, interaction.guild):
        error_embed = discord.Embed(
            title=f"Permission Denied {failed_emoji}",
            description="You are not allowed to use this command.",
            colour=0xE74C3C
        )
        error_embed.set_footer(text=f"Attempted by {user}", icon_url=user.display_avatar.url)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    try:
        async with session.post(
            f"{API_BASE}/command",
            headers={"server-key": API_KEY},
            json={"command": command}
        ) as resp:
            if resp.status != 200:
                msg = get_erlc_error_message(resp.status)
                error_embed = discord.Embed(
                    title=f"Command Error {failed_emoji}",
                    description=msg,
                    colour=0xE74C3C
                )
                error_embed.set_footer(text=f"Attempted by {user}", icon_url=user.display_avatar.url)
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return

            success_embed = discord.Embed(
                title=f"Command Sent {tick_emoji}",
                description=f"The command `{command}` has been sent successfully!",
                colour=0x1E77BE
            )
            success_embed.set_footer(text=f"Requested by {user}", icon_url=user.display_avatar.url)
            await interaction.response.send_message(embed=success_embed, ephemeral=True)

    except Exception as e:
        msg = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(
            title=f"Command Error {failed_emoji}",
            description=msg,
            colour=0xE74C3C
        )
        error_embed.set_footer(text=f"Attempted by {user}", icon_url=user.display_avatar.url)
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Log usage
    await log_command(user, command)

def all_players_in_discord_embed(guild: discord.Guild) -> discord.Embed:
    """Embed when all players are in Discord"""
    embed = discord.Embed(
        title="Discord Check",
        description=f"{tick_emoji} All players are in the Discord!",
        color=0x1E77BE,
    )
    embed.set_author(name=guild.name, icon_url=guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed


async def fetch_discord_check_embed(guild: discord.Guild) -> discord.Embed | None:
    """Fetch players from API, compare to guild members, and build embed"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"server-key": API_KEY}
            async with session.get(f"{API_BASE}/players", headers=headers) as res:
                if res.status == 422:  # No players
                    return all_players_in_discord_embed(guild)
                if res.status != 200:
                    raise Exception(await res.text())
                data = await res.json()
                players = [p["Player"].split(":")[0] for p in data]

        # Collect guild member names
        guild_members = [m.display_name for m in guild.members] + [m.name for m in guild.members]

        # Check which Roblox names are not in Discord
        not_in_discord = []
        for roblox_name in players:
            pattern = re.compile(rf"\b{re.escape(roblox_name)}\b", re.IGNORECASE)
            if not any(pattern.search(name) for name in guild_members):
                not_in_discord.append(roblox_name)

        # Build embed
        if not_in_discord:
            formatted = "\n".join(
                f"[{u}](https://www.roblox.com/users/profile?username={u})"
                for u in not_in_discord
            )
            embed = discord.Embed(
                title="Discord Check",
                description=f"There are **{len(not_in_discord)}** players **NOT** in the Discord!\n> {formatted}",
                color=0x1E77BE,
            )
        else:
            embed = all_players_in_discord_embed(guild)

        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return embed

    except Exception as e:
        print(f"Error fetching Discord check: {e}")
        return None

# ---------------------- /discord check ----------------------

@discord_group.command(name="check", description="Check which players are not in the Discord.")
async def discord_check(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await fetch_discord_check_embed(interaction.guild)
    if embed:
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(get_erlc_error_message(0, exception="Failed to fetch check"))

# ---------------------- /erlc code ----------------------

@erlc_group.command(name="code", description="Shows the ER:LC server code.")
async def erlc_code(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        headers = {"server-key": API_KEY}

        # Fetch server info
        async with session.get(f"{API_BASE}", headers=headers) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(
                    await get_erlc_error_message(resp), ephemeral=True
                )
            server_data = await resp.json()
            erlc_code = server_data.get("JoinKey", "Unknown")

    embed = discord.Embed(
        title="ER:LC Code",
        description=f"The ER:LC code is `{erlc_code}`.",
        colour=0x1E77BE,
    )

    embed.set_author(
        name=interaction.guild.name,
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")

    await interaction.response.send_message(embed=embed)

# ---------------------- /erlc kills ----------------------

@erlc_group.command(name="kills", description="Shows the recent ER:LC kill logs.")
async def erlc_kills(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        headers = {"server-key": API_KEY}
        try:
            async with session.get(f"{API_BASE}/killlogs", headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.response.send_message(
                        await get_erlc_error_message(resp), ephemeral=True
                    )
                data = await resp.json()
        except Exception as e:
            return await interaction.response.send_message(
                f"{failed_emoji} Failed to fetch kill logs: `{e}`", ephemeral=True
            )

    if not data:
        description = "> There have not been any kill logs in-game."
    else:
        description = "\n".join(format_kill_entry(entry) for entry in data)

    embed = discord.Embed(
        title=f"ER:LC Kill logs ({len(data)})",
        description=description,
        colour=0x1E77BE,
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    embed.set_author(
        name=interaction.guild.name,
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
    )
    await interaction.response.send_message(embed=embed)

# ---------------------- /erlc players ----------------------

@erlc_group.command(name="players", description="Shows the current players in ER:LC.")
async def erlc_players(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        headers={"server-key": API_KEY}

        # Fetch server info
        async with session.get(f"{API_BASE}", headers=headers) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(
                    await get_erlc_error_message(resp), ephemeral=True
                )
            server_data = await resp.json()
            player_count = server_data.get("CurrentPlayers", 0)
            max_player_count = server_data.get("MaxPlayers", 0)

        # Fetch players
        async with session.get(f"{API_BASE}/players", headers=headers) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(
                    await get_erlc_error_message(resp), ephemeral=True
                )
            players_data = await resp.json()

        # Build description
        if not players_data or player_count == 0:
            description = "> There are no players in-game."
        else:
            description = "\n".join(
                [
                    f'> [{p["Player"].split(":")[0]}](https://www.roblox.com/users/{p["Player"].split(":")[1]}/profile)'
                    for p in players_data
                ]
            )

        embed = discord.Embed(
            title=f"ER:LC Players ({player_count}/{max_player_count})",
            description=description,
            colour=0x1E77BE,
        )

        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")

        await interaction.response.send_message(embed=embed)

# ---------------------- prefix commands that have discord at the start .discord check ----------------------

@bot.command(name="discord")
async def discord_cmd(ctx, subcommand: str = None):
    if not subcommand or subcommand.lower() != "check":
        await ctx.send("❌ Unknown command. Please use `/discord check`.")
        return
    try:
        async with ctx.typing():
            embed = await fetch_discord_check_embed(ctx.guild)
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(get_erlc_error_message(0, exception=e))

# --

PLAYERCOUNT_VC_ID = 1381697147895939233  
QUEUE_VC_ID = 1381697165562347671         
PLAYERCOUNT_PREFIX = "「🎮」In Game:"
QUEUE_PREFIX = "「⏳」In Queue:"
CODE_PREFIX = "「🔑」Code:"
SERVERNAME_PREFIX = "「🏷️」Server:"
CODE_VC_ID = 1387116991814439042
SERVERNAME_VC_ID = 1423033498255626280
TEAM_KICK_USAGE_LOG_CHANNEL_ID = "1381267054354632745"
CHECK_CHANNEL_ID = 1381267054354632745
YOUR_GUILD_ID = 1343179590247645205  

# --- Helper to fetch JSON ---
async def fetch_json(session: aiohttp.ClientSession, path: str, server_key: str):
    url = f"{API_BASE}{path}"  # API_BASE ends with /server
    headers = {"Server-Key": server_key}
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
            logger.warning(f"⚠️ API returned {resp.status} for {url}")
    except Exception as e:
        logger.error(f"❌ Exception fetching {url}: {e}")
    return None

# --- Loop task: players + queue ---
@tasks.loop(seconds=180)
async def update_vc_status():
    #logger.info("🔄 Running VC update loop...")
    guild = bot.get_guild(1343179590247645205)
    if not guild:
        logger.warning("⚠️ Guild not found.")
        return

    async with aiohttp.ClientSession() as session:
        # Fetch server info
        server_info = await fetch_json(session, "", API_KEY)
        player_count = server_info.get("CurrentPlayers", 0) if server_info else 0
        max_players = server_info.get("MaxPlayers", 0) if server_info else 0

        # Fetch queue count
        queue_data = await fetch_json(session, "/queue", API_KEY)
        queue_count = len(queue_data) if isinstance(queue_data, list) else 0

    # Update VC names only if changed
    try:
        if (player_vc := guild.get_channel(PLAYERCOUNT_VC_ID)):
            new_name = f"{PLAYERCOUNT_PREFIX} {player_count}/{max_players}"
            if player_vc.name != new_name:
                await player_vc.edit(name=new_name)
                await asyncio.sleep(10)

        if (queue_vc := guild.get_channel(QUEUE_VC_ID)):
            new_name = f"{QUEUE_PREFIX} {queue_count}"
            if queue_vc.name != new_name:
                await queue_vc.edit(name=new_name)
                await asyncio.sleep(10)

        #logger.info(f"✅ Updated VC names: Players={player_count}/{max_players}, Queue={queue_count}")

    except Exception as e:
        logger.error(f"❌ Failed to update VC names: {e}")

# -

# ---------------------- Helpers ----------------------
async def update_vc_name_api(
    ctx,
    api_field: str,
    channel_id: int,
    name_format: str,
    success_message: str,
):
    """Generic helper for updating a VC name based on API field."""
    if ctx.author.id != OWNER_ID:
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.HTTPException as e:
            print(f"[WARN] Failed to react with failed_emoji: {e}")
        return

    async with aiohttp.ClientSession() as session:
        server_info = await fetch_json(session, "", API_KEY)
        if not server_info:
            await ctx.send("❌ Failed to fetch server info.")
            return
        field_value = server_info.get(api_field, "N/A")

    guild = ctx.guild
    if not guild:
        return
    vc = guild.get_channel(channel_id)
    if vc:
        new_name = name_format.format(value=field_value)
        if vc.name != new_name:
            try:
                await vc.edit(name=new_name)
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to edit that VC.")
                return
            except discord.HTTPException as e:
                await ctx.send(f"❌ Failed to update VC name: {e}")
                print(f"[WARN] Failed to update VC name: {e}")
                return

    try:
        await ctx.message.add_reaction(tick_emoji)
    except discord.HTTPException as e:
        print(f"[WARN] Failed to react with tick_emoji: {e}")

    await ctx.send(success_message.format(value=field_value))



@bot.command(name="joincode")
async def join_code(ctx):
    """Owner-only: update join code VC"""
    await update_vc_name_api(
        ctx,
        api_field="JoinKey",
        channel_id=CODE_VC_ID,
        name_format="「🔑」Code: {value}",
        success_message="✅ Join code VC updated to: `{value}`",
    )


@bot.command(name="servername")
async def server_name(ctx):
    """Owner-only: update server name VC"""
    await update_vc_name_api(
        ctx,
        api_field="Name",
        channel_id=SERVERNAME_VC_ID,
        name_format=f"{SERVERNAME_PREFIX} {{value}}",
        success_message="✅ Server name VC updated to: `{value}`",
    )



# ---------------------- BACKGROUND TASK ----------------------
previous_not_in_discord = set()  # global to track changes

@tasks.loop(seconds=600)
async def discord_check_task():
    global previous_not_in_discord
    guild = bot.get_guild(YOUR_GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(CHECK_CHANNEL_ID)
    if not channel:
        return

    embed = await fetch_discord_check_embed(guild)
    if embed and "NOT" in embed.description:
        current_not_in_discord = set(re.findall(r"\[([^\]]+)\]", embed.description))
        if current_not_in_discord != previous_not_in_discord:
            await channel.send(embed=embed)
            previous_not_in_discord = current_not_in_discord

async def send_to_game(command: str):
    headers = {"Server-Key": API_KEY}
    data = {"command": command}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{API_BASE}/command", headers=headers, json=data) as resp:
                if resp.status != 200:
                    try:
                        err_json = await resp.json()
                        api_code = err_json.get("code")
                    except Exception:
                        api_code = None

                    # Check for Server Offline (3002) and ignore it
                    if api_code == 3002 or "3002" in str(await resp.text()):
                    #    print(f"[DEBUG {datetime.now(timezone.utc)}] Server offline, cannot send command: {command}")
                        return

                    # Otherwise, raise the error as usual
                    err_msg = get_erlc_error_message(resp.status, api_code)
                    raise Exception(err_msg)

        except Exception as e:
            # Catch all other exceptions and log
            err_msg = get_erlc_error_message(0, exception=e)
           # print(f"[DEBUG {datetime.now(timezone.utc)}] Exception sending command: {err_msg}")


async def run_teamkick_sequence(roblox_user: str, reason: str):
    """Run the in-game commands to perform a teamkick in ERLC."""
    await send_to_game(f":wanted {roblox_user}")
    await asyncio.sleep(20)
    await send_to_game(f":pm {roblox_user} You have been kicked off the team for: {reason}")
    await asyncio.sleep(20)
    await send_to_game(f":unwanted {roblox_user}")


def build_teamkick_success_embed(user: discord.User, roblox_user: str, reason: str) -> discord.Embed:
    """Build success embed for both prefix and slash teamkick commands."""
    embed = discord.Embed(
        title="✅ Team Kick Successful",
        description=(
            f"`{roblox_user}` has been kicked off the team.\n\n"
            f"**Reason:** {reason}\n"
            f"**Moderator:** [{user}](https://discord.com/users/{user.id})"
        ),
        colour=discord.Color.green()
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed


def build_teamkick_error_embed(e: Exception) -> discord.Embed:
    """Build error embed for failed teamkick attempts."""
    err_msg = get_erlc_error_message(0, exception=e)
    embed = discord.Embed(
        title="❌ ERLC API Error",
        description=err_msg,
        colour=discord.Color.red()
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed


def build_permission_denied_embed(prefix=False) -> discord.Embed:
    """Permission denied embed, prefix/slash variants."""
    emoji = error_emoji if prefix else "❌"
    return discord.Embed(
        title="Permission Denied",
        description=f"{emoji} You do not have permission to use this command.",
        colour=discord.Color.red()
    )


def build_status_embed(roblox_user: str) -> discord.Embed:
    """Status embed while processing the teamkick."""
    return discord.Embed(
        title="⏳ Processing Team Kick",
        description=f"Processing team kick for `{roblox_user}`...",
        colour=0x1E77BE
    )

@erlc_group.command(name="teamkick", description="Kick a Roblox player off a team (up to 1m to be done)")
@app_commands.describe(roblox_user="Roblox username to kick", reason="Reason for team kick")
async def teamkick(interaction: discord.Interaction, roblox_user: str, reason: str):
    user = interaction.user
    has_staff_role = any(r.id == staff_role_id for r in user.roles)
    is_owner = user.id == OWNER_ID

    if not has_staff_role and not is_owner:
        return await interaction.response.send_message(embed=build_permission_denied_embed(), ephemeral=True)

    await interaction.response.send_message(embed=build_status_embed(roblox_user), ephemeral=True)

    try:
        await run_teamkick_sequence(roblox_user, reason)
    except Exception as e:
        return await interaction.followup.send(embed=build_teamkick_error_embed(e), ephemeral=True)

    # ✅ Log command correctly
    await log_command(
        user=user,
        command=f"/erlc teamkick {roblox_user} {reason}"
    )

    await interaction.followup.send(embed=build_teamkick_success_embed(user, roblox_user, reason), ephemeral=True)

# ----------------------

# --- /erlc bans (SLASH COMMAND) ---
@erlc_group.command(name="bans", description="List active ER:LC bans (staff only, owner bypass)")
async def erlc_bans(interaction: discord.Interaction):
    user = interaction.user
    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Colour.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    await interaction.response.defer(thinking=True)

    try:
        bans_data = await fetch_api_data(f"{API_BASE}/bans")

        count = len(bans_data) if bans_data else 0
        description = "\n".join(f"> {b['Username']}" for b in bans_data) if bans_data else "> No bans found."

        embed = discord.Embed(
            title=f"ER:LC Bans ({count})",
            description=description,
            colour=0x1E77BE
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_footer(text=interaction.guild.name)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        error = get_erlc_error_message(0, exception=e)
        embed = discord.Embed(
            title="❌ ERLC API Error",
            description=error,
            colour=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await interaction.followup.send(embed=embed, ephemeral=True)

#--

# --- Helper to parse Roblox user string ---
def parse_player(player):
    if not player:
        return ("Unknown", None)
    parts = player.rsplit(":", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (player, None)


#-


@erlc_group.command(name="logs", description="Show ER:LC in-game command logs")
async def erlc_logs(interaction: discord.Interaction):
    user = interaction.user
    if user.id != OWNER_ID:
        role = interaction.guild.get_role(staff_role_id)
        if not role or role not in user.roles:
            return await interaction.response.send_message(
                "❌ You don’t have permission to use this command.", ephemeral=True
            )

    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/commandlogs", headers={"server-key": API_KEY}) as r:
            if r.status != 200:
                return await interaction.followup.send(
                    f"⚠️ API error {r.status}", ephemeral=True
                )
            logs = await r.json()

    embed = discord.Embed(title=f"ER:LC Logs ({len(logs)})", colour=0x1E77BE)

    if interaction.guild:
        icon = interaction.guild.icon.url if interaction.guild.icon else None
        embed.set_author(name=interaction.guild.name, icon_url=icon)
        embed.set_footer(text=f"Running {BOT_VERSION}")

    if not logs:
        embed.description = "There are no logs in-game."
        return await interaction.followup.send(embed=embed)

    lines = []
    for entry in logs[:10]:
        name, rid = parse_player(entry.get("Player"))
        cmd = discord.utils.escape_markdown(entry.get("Command", ""))
        ts = entry.get("Timestamp")
        if isinstance(ts, (int, float)):
            t = f"<t:{int(ts)}:F>"
            if rid:
                lines.append(f"[{name}](https://www.roblox.com/users/{rid}/profile) used `{cmd}` at {t}")
            else:
                lines.append(f"{name} used `{cmd}` at {t}")

    if len(logs) > 10:
        lines.append(f"...and {len(logs) - 10} more logs not shown.")

    embed.description = "\n".join(lines)
    await interaction.followup.send(embed=embed)

#--

async def fetch_erlc_logs() -> list:
    """Fetch ER:LC logs from the external API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/commandlogs", headers={"server-key": API_KEY}) as r:
            if r.status != 200:
                raise RuntimeError(f"API error {r.status}")
            return await r.json()


def build_erlc_embed(guild: discord.Guild, logs: list) -> discord.Embed:
    """Create an embed displaying ER:LC logs."""
    embed = discord.Embed(
        title=f"ER:LC Logs ({len(logs)})",
        colour=discord.Color.blue(),
        timestamp=datetime.now()
    )

    # Author & footer
    if guild:
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        embed.set_footer(text=f"Running {BOT_VERSION}")

    # No logs found
    if not logs:
        embed.description = "There are no logs in-game."
        return embed

    # Format log entries
    lines = [format_log_entry(entry) for entry in logs[:10]]
    if len(logs) > 10:
        lines.append(f"...and {len(logs) - 10} more logs not shown.")

    embed.description = "\n".join(lines)
    return embed


def format_log_entry(entry: dict) -> str:
    """Format a single log entry for display."""
    name, rid = parse_player(entry.get("Player"))
    cmd = discord.utils.escape_markdown(entry.get("Command", ""))
    ts = entry.get("Timestamp")
    t = f"<t:{int(ts)}:F>" if isinstance(ts, (int, float)) else "Unknown time"

    if rid:
        return f"[{name}](https://www.roblox.com/users/{rid}/profile) used `{cmd}` at {t}"
    return f"{name} used `{cmd}` at {t}"

# ---------------------- prefix commands that have erlc at the start .erlc info, .erlc players, .erlc code, .erlc kills, .erlc command ----------------------

@bot.command(name="erlc")
async def erlc(ctx, subcommand: str = None, roblox_user: str = None, *, reason: str = None):
    if not subcommand:
        return await ctx.send("❌ Unknown command. Please use the `/erlc` slash command.")

    subcommand = subcommand.lower()
    handlers = {
        "info": handle_erlc_info,
        "players": handle_erlc_players,
        "code": handle_erlc_code,
        "kills": handle_erlc_kills,
        "command": handle_erlc_command,
        "teamkick": handle_erlc_teamkick,
        "bans": handle_erlc_bans,
        "logs": handle_erlc_logs,
        "joins": handle_erlc_joins,
        "modcalls": handle_erlc_modcalls,
        "vehicles": handle_erlc_vehicles,
    }

    handler = handlers.get(subcommand)
    if not handler:
        return await ctx.send(f"❌ Unknown subcommand `{subcommand}`. Please use the `/erlc` slash command.")

    # Pass extra args only if needed
    if subcommand == "teamkick":
        await handler(ctx, roblox_user=roblox_user, reason=reason)
    elif subcommand == "logs":
        await handler(ctx, is_interaction=False)
    else:
        await handler(ctx)

# --- Handler: .erlc vehicles ---
async def handle_erlc_vehicles(ctx):
    user = ctx.author
    guild = ctx.guild
    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    if not has_staff_role and not is_owner:
        embed = discord.Embed(title="Permission Denied",
                              description="❌ You do not have permission to use this command.",
                              colour=discord.Colour.red())
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return await ctx.send(embed=embed)

    bypass_message = None
    if is_owner and not has_staff_role:
        bypass_embed = discord.Embed(description="⏳ Bypassing checks...", colour=discord.Color.gold())
        bypass_message = await ctx.send(embed=bypass_embed)
        await asyncio.sleep(1.2)
    else:
        # show typing
        async with ctx.typing():
            pass

    try:
        vehicles = await fetch_api_data(f"{API_BASE}/vehicles")

        if not vehicles:
            description = "> There are no spawned vehicles in the server."
            count = 0
        else:
            lines = []
            for v in vehicles:
                name = v.get("Name", "Unknown Vehicle")
                texture = v.get("Texture", "Unknown")
                owner_raw = v.get("Owner", "")

                owner_display = await resolve_roblox_owner_link(owner_raw)
                lines.append(f"> **{name}** — `{texture}` (Owner: {owner_display})")

            count = len(lines)
            description = "\n".join(lines)

        embed = discord.Embed(title=f"ER:LC Vehicles ({count})", description=description, colour=0x1E77BE)
        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    except Exception as e:
        err = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(title="❌ ERLC API Error", description=err, colour=discord.Color.red())
        error_embed.set_footer(text=f"Running {BOT_VERSION}")
        if bypass_message:
            await bypass_message.edit(embed=error_embed)
        else:
            await ctx.send(embed=error_embed)




# --- Handler: .erlc modcalls ---
async def handle_erlc_modcalls(ctx):
    user = ctx.author
    guild = ctx.guild

    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    # --- Permission Check ---
    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return await ctx.send(embed=embed)

    # --- Owner Bypass Embed ---
    bypass_message = None
    if is_owner and not has_staff_role:
        bypass_embed = discord.Embed(
            description="⏳ Bypassing checks...",
            colour=discord.Color.gold()
        )
        bypass_message = await ctx.send(embed=bypass_embed)
        await asyncio.sleep(1.5)
    else:
        await ctx.typing()

    try:
        # Fetch mod call logs
        modcalls = await fetch_api_data(f"{API_BASE}/modcalls")

        if not modcalls:
            description = "> There are no recent moderator call logs."
            count = 0
        else:
            entries = []
            for entry in modcalls:
                caller_str = entry.get("Caller", "Unknown:0")
                moderator_str = entry.get("Moderator", None)
                timestamp = entry.get("Timestamp", 0)

                caller_name, caller_id = parse_player(caller_str)
                caller_link = f"[{caller_name}](https://www.roblox.com/users/{caller_id}/profile)" if caller_id else caller_name

                if moderator_str:
                    mod_name, mod_id = parse_player(moderator_str)
                    mod_link = f"[{mod_name}](https://www.roblox.com/users/{mod_id}/profile)" if mod_id else mod_name
                    entries.append(f"> {caller_link} called for a mod <t:{timestamp}:R>, handled by {mod_link}")
                else:
                    entries.append(f"> {caller_link} called for a mod <t:{timestamp}:R> (unanswered)")

            count = len(entries)
            description = "\n".join(entries)

        # Create embed
        embed = discord.Embed(
            title=f"ER:LC ModCall Logs ({count})",
            description=description,
            colour=0x1E77BE
        )

        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        # Send final embed
        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    except Exception as e:
        error = get_erlc_error_message(0, exception=e)
        embed = discord.Embed(
            title="❌ ERLC API Error",
            description=error,
            colour=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)


# --- Handler: .erlc joins ---
async def handle_erlc_joins(ctx):
    user = ctx.author
    guild = ctx.guild

    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == OWNER_ID

    # --- Permission Check ---
    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return await ctx.send(embed=embed)

    # --- Owner Bypass ---
    if is_owner and not has_staff_role:
        # Send "bypass" embed publicly
        bypass_embed = discord.Embed(
            description=f"⏳ Bypassing checks...",
            colour=discord.Color.gold()
        )
        bypass_message = await ctx.send(embed=bypass_embed)
        await asyncio.sleep(1.5)
    else:
        # Staff get typing indicator
        await ctx.typing()
        bypass_message = None

    try:
        # Fetch join/leave logs
        join_logs = await fetch_api_data(f"{API_BASE}/joinlogs")

        if not join_logs:
            description = "> There are no recent join/leave logs."
            count = 0
        else:
            entries = []
            for entry in join_logs:
                player_str = entry.get("Player", "Unknown:0")
                timestamp = entry.get("Timestamp", 0)
                joined = entry.get("Join", True)

                username, player_id = parse_player(player_str)
                user_link = (
                    f"[{username}](https://www.roblox.com/users/{player_id}/profile)"
                    if player_id else username
                )

                if joined:
                    entries.append(f"> {user_link} joined the server at <t:{timestamp}:R>")
                else:
                    entries.append(f"> {user_link} left the server at <t:{timestamp}:R>")

            count = len(entries)
            description = "\n".join(entries)

        # Create the embed
        embed = discord.Embed(
            title=f"ER:LC Join/Leave Logs ({count})",
            description=description,
            colour=0x1E77BE
        )

        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        # Edit or send
        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    except Exception as e:
        error = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(
            title="❌ ERLC API Error",
            description=error,
            colour=discord.Color.red()
        )
        error_embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=error_embed)
        else:
            await ctx.send(embed=error_embed)


# --- Handler: erlc logs ---
async def handle_erlc_logs(ctx_or_interaction, is_interaction: bool):
    """Handles command to display ER:LC logs in an embed."""
    user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author
    guild = ctx_or_interaction.guild

    # Permission check
    if not await has_permission(user, guild):
        msg = "❌ You don’t have permission to use this command."
        return await send_response(ctx_or_interaction, msg, is_interaction, ephemeral=True)

    if is_interaction:
        await ctx_or_interaction.response.defer()

    # Fetch logs
    try:
        logs = await fetch_erlc_logs()
    except RuntimeError as e:
        return await send_response(ctx_or_interaction, f"⚠️ {e}", is_interaction, ephemeral=True)

    # Build and send embed
    embed = build_erlc_embed(guild, logs)
    await send_response(ctx_or_interaction, embed=embed, is_interaction=is_interaction)


async def has_permission(user: discord.Member, guild: discord.Guild) -> bool:
    """Check if the user has permission to run the command."""
    if user.id == OWNER_ID:
        return True
    role = guild.get_role(staff_role_id)
    return role and role in user.roles


async def send_response(ctx_or_interaction, content=None, embed=None, is_interaction=False, ephemeral=False):
    """Send a response depending on the context type."""
    if is_interaction:
        if content and not embed:
            await ctx_or_interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await ctx_or_interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        if content and not embed:
            await ctx_or_interaction.send(content)
        else:
            await ctx_or_interaction.send(embed=embed)

# --- Handler: .erlc bans ---
async def handle_erlc_bans(ctx):
    user = ctx.author
    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Color.red()
        )
        return await ctx.send(embed=embed)

    async with ctx.typing():
        try:
            bans_data = await fetch_api_data(f"{API_BASE}/bans")
            count = len(bans_data) if bans_data else 0
            description = "\n".join(f"> {b['Username']}" for b in bans_data) if bans_data else "> No bans found."

            embed = discord.Embed(
                title=f"ER:LC Bans ({count})",
                description=description,
                colour=0x1E77BE
            )

            guild = ctx.guild
            if guild:
                embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
                embed.set_footer(text=guild.name)
            else:
                embed.set_footer(text=f"Running {BOT_VERSION}")

            await ctx.send(embed=embed)

        except Exception as e:
            error = get_erlc_error_message(0, exception=e)
            embed = discord.Embed(
                title="❌ ERLC API Error",
                description=error,
                colour=discord.Color.red()
            )
            embed.set_footer(text=f"Running {BOT_VERSION}")
            await ctx.send(embed=embed)


# --- Handler: .erlc teamkick ---
async def handle_erlc_teamkick(ctx, roblox_user=None, *, reason=None):
    if not roblox_user or not reason:
        return await ctx.send(f"❌ Usage: `{COMMAND_PREFIX}erlc teamkick <roblox_user> <reason>`")

    user = ctx.author
    has_staff_role = any(r.id == staff_role_id for r in user.roles)
    is_owner = user.id == OWNER_ID

    if not has_staff_role and not is_owner:
        try:
            await ctx.message.add_reaction(failed_emoji)
        except discord.HTTPException:
            pass
        return await ctx.send(embed=build_permission_denied_embed(prefix=True))

    # React with ✅ to show command received
    try:
        await ctx.message.add_reaction(tick_emoji)
    except discord.HTTPException:
        pass

    # Show processing embed
    await ctx.send(embed=build_status_embed(roblox_user))

    # Run in-game sequence
    try:
        await run_teamkick_sequence(roblox_user, reason)
    except Exception as e:
        return await ctx.send(embed=build_teamkick_error_embed(e))

    # Log the command — only actual parameters allowed
    await log_command(
        user=user,
        command=f"{COMMAND_PREFIX}erlc teamkick {roblox_user} {reason}"
    )

    # Send success embed
    await ctx.send(embed=build_teamkick_success_embed(user, roblox_user, reason), ephemeral=True)




# --- Handler: .erlc info ---
async def handle_erlc_info(ctx):
    try:
        async with ctx.typing():
            embed = await erlc_info_embed(ctx)
            view = InfoView(ctx, lambda: erlc_info_embed(ctx))
            await ctx.send(embed=embed, view=view)
    except Exception as e:
        await report_erlc_error(ctx, e, ".erlc info")


async def handle_erlc_players(ctx):
    try:
        async with ctx.typing():
            server_data = await fetch_api_data(API_BASE)
            players_data = await fetch_api_data(f"{API_BASE}/players")

            player_count = server_data.get("CurrentPlayers", 0)
            max_player_count = server_data.get("MaxPlayers", 0)

            if not players_data or player_count == 0:
                description = "> There are no players in-game."
            else:
                description = "\n".join(
                    [
                        f'> [{p["Player"].split(":")[0]}](https://www.roblox.com/users/{p["Player"].split(":")[1]}/profile)'
                        for p in players_data
                    ]
                )

            embed = create_embed(
                ctx,
                title=f"ER:LC Players ({player_count}/{max_player_count})",
                description=description,
            )
            await ctx.send(embed=embed)
    except Exception as e:
        await report_erlc_error(ctx, e, ".erlc players")


async def handle_erlc_code(ctx):
    try:
        async with ctx.typing():
            server_data = await fetch_api_data(API_BASE)
            erlc_code = server_data.get("JoinKey", "Unknown")
            embed = create_embed(
                ctx,
                title="ER:LC Code",
                description=f"The ER:LC code is `{erlc_code}`."
            )
            await ctx.send(embed=embed)
    except Exception as e:
        await report_erlc_error(ctx, e, ".erlc code")


async def handle_erlc_kills(ctx):
    try:
        async with ctx.typing():
            data = await fetch_api_data(f"{API_BASE}/killlogs")
            if not data:
                description = "> There have not been any kill logs in-game."
            else:
                description = "\n".join(format_kill_entry(e) for e in data)

            embed = create_embed(
                ctx,
                title=f"ER:LC Kill logs ({len(data)})",
                description=description
            )
            await ctx.send(embed=embed)
    except Exception as e:
        await report_erlc_error(ctx, e, ".erlc kills")


async def handle_erlc_command(ctx):
    await ctx.send("Please use the `/erlc command` slash command.")


# --- Utility Functions ---

async def fetch_api_data(url):
    async with aiohttp.ClientSession() as session:
        headers = {"server-key": API_KEY}
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise ValueError(f"API request failed: {resp.status}")
            return await resp.json()


def create_embed(ctx, title, description):
    embed = discord.Embed(title=title, description=description, colour=0x1E77BE)
    embed.set_author(
        name=ctx.guild.name,
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
    )
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed


def format_kill_entry(entry):
    ts = entry.get("Timestamp", 0)
    killer_name, killer_id = parse_player(entry.get("Killer", "Unknown:0"))
    victim_name, victim_id = parse_player(entry.get("Killed", "Unknown:0"))
    killer_link = f"[{killer_name}](https://www.roblox.com/users/{killer_id}/profile)" if killer_id != "0" else killer_name
    victim_link = f"[{victim_name}](https://www.roblox.com/users/{victim_id}/profile)" if victim_id != "0" else victim_name
    return f"{killer_link} killed {victim_link} at <t:{ts}:F>"


def parse_player(player_raw):
    if ":" in player_raw:
        name, id_str = player_raw.split(":", 1)
    else:
        name, id_str = player_raw, "0"
    return name, id_str


async def report_erlc_error(ctx, exception, context):
    error_message = await get_erlc_error_message(0, exception=exception)
    await ctx.send(error_message)
    print(f"[ERROR] {context} failed: {exception}")





#--

SUGGESTION_CHANNEL_ID = 1343622169086918758 
STAFF_SUGGESTION_CHANNEL_ID = 1373704702977376297 
SUGGESTION_LOG_CHANNEL_ID = 1381267054354632745  
STAFF_SUGGEST_LOG_CHANNEL_ID = 1381267054354632745  

# ============================================================
# LOGGING FUNCTION
# ============================================================
async def log_suggestion(action: str, suggester: discord.User, suggestion: str, channel: discord.TextChannel, guild: discord.Guild):
    """
    Logs a suggestion action (Created, Upvote, Downvote, Approved, Denied) to a channel.
    """
    embed = discord.Embed(
        title=f"Suggestion Log: {action}",
        description=suggestion,
        color=0x1E77BE,
    )

    # Set guild name and icon if available
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
    else:
        embed.set_author(name=guild.name)

    embed.set_footer(text=f"Running {BOT_VERSION}")

    # Discord formatted user + timestamp
    unix_ts = int(time.time())
    embed.add_field(
        name="User",
        value=f"[{suggester}](https://discord.com/users/{suggester.id}) ({suggester.id})",
        inline=True
    )
    embed.add_field(
        name="Time",
        value=f"<t:{unix_ts}:F>",
        inline=True
    )

    await channel.send(embed=embed)


# ============================================================
# VIEW CLASS FOR SUGGESTIONS
# ============================================================
class SuggestionView(discord.ui.View):
    def __init__(self, author: discord.User, approver_role_id=None, staff_mode=False):
        super().__init__(timeout=None)
        self.votes = {"up": set(), "down": set()}
        self.author = author
        self.staff_mode = staff_mode
        self.approver_role_id = approver_role_id

    async def update_embed(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="👍 Upvotes", value=str(len(self.votes["up"])), inline=True)
        embed.set_field_at(1, name="👎 Downvotes", value=str(len(self.votes["down"])), inline=True)
        await interaction.message.edit(embed=embed, view=self)

        # Log upvote/downvote
        log_channel_id = STAFF_SUGGEST_LOG_CHANNEL_ID if self.staff_mode else SUGGESTION_LOG_CHANNEL_ID
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            last_user = interaction.user
            if last_user.id in self.votes["up"]:
                action = "Upvote"
            elif last_user.id in self.votes["down"]:
                action = "Downvote"
            else:
                action = "Vote Removed"
            await log_suggestion(action, last_user, embed.description, log_channel, interaction.guild)

    @discord.ui.button(label="Upvote", style=discord.ButtonStyle.green, emoji="👍", row=0)
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid in self.votes["up"]:
            self.votes["up"].remove(uid)
        else:
            self.votes["up"].add(uid)
            self.votes["down"].discard(uid)
        await self.update_embed(interaction)
        await interaction.response.defer()

    @discord.ui.button(label="Downvote", style=discord.ButtonStyle.red, emoji="👎", row=0)
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid in self.votes["down"]:
            self.votes["down"].remove(uid)
        else:
            self.votes["down"].add(uid)
            self.votes["up"].discard(uid)
        await self.update_embed(interaction)
        await interaction.response.defer()

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.blurple, emoji=f"{tick_emoji}", row=1)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        approver_role = discord.utils.get(interaction.guild.roles, id=self.approver_role_id)
        if approver_role not in interaction.user.roles:
            embed = discord.Embed(
                description=f"{staff_emoji} You don't have permission to approve this suggestion.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = f"{tick_emoji} {embed.title} (Approved)"
        await interaction.message.edit(embed=embed, view=None)

        # DM author
        try:
            dm_embed = discord.Embed(
                title=f"{tick_emoji} Your suggestion was approved!",
                description=embed.description,
                color=discord.Color.green()
            )
            await self.author.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # Log approval
        log_channel_id = STAFF_SUGGEST_LOG_CHANNEL_ID if self.staff_mode else SUGGESTION_LOG_CHANNEL_ID
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            await log_suggestion("Approved", interaction.user, embed.description, log_channel, interaction.guild)

        confirm = discord.Embed(description=f"{tick_emoji} Suggestion approved.", color=discord.Color.green())
        await interaction.response.send_message(embed=confirm, ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.gray, emoji=f"{failed_emoji}", row=1)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        approver_role = discord.utils.get(interaction.guild.roles, id=self.approver_role_id)
        if approver_role not in interaction.user.roles:
            embed = discord.Embed(
                description=f"{staff_emoji} You don't have permission to deny this suggestion.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = f"{failed_emoji} {embed.title} (Denied)"
        await interaction.message.edit(embed=embed, view=None)

        # DM author
        try:
            dm_embed = discord.Embed(
                title=f"{failed_emoji} Your suggestion was denied.",
                description=embed.description,
                color=discord.Color.red()
            )
            await self.author.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # Log denial
        log_channel_id = STAFF_SUGGEST_LOG_CHANNEL_ID if self.staff_mode else SUGGESTION_LOG_CHANNEL_ID
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            await log_suggestion("Denied", interaction.user, embed.description, log_channel, interaction.guild)

        confirm = discord.Embed(description=f"{error_emoji} Suggestion denied.", color=discord.Color.red())
        await interaction.response.send_message(embed=confirm, ephemeral=True)

# ============================================================
# HELPER FUNCTION
# ============================================================
async def post_suggestion(user: discord.User, suggestion: str, guild: discord.Guild, staff_mode=False):
    """Post a suggestion embed to the correct channel."""
    channel_id = STAFF_SUGGESTION_CHANNEL_ID if staff_mode else SUGGESTION_CHANNEL_ID
    log_channel_id = STAFF_SUGGEST_LOG_CHANNEL_ID if staff_mode else SUGGESTION_LOG_CHANNEL_ID
    channel = bot.get_channel(channel_id)
    log_channel = bot.get_channel(log_channel_id)
    if not channel:
        return None, log_channel

    title = "💡 New Staff Suggestion" if staff_mode else "💡 New Suggestion"
    color = 0x1E77BE if staff_mode else 0x1E77BE

    embed = discord.Embed(title=title, description=suggestion, color=color)
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
    else:
        embed.set_author(name=guild.name)
    embed.set_footer(text=f"Running {BOT_VERSION}")

    embed.add_field(name="👍 Upvotes", value="0", inline=True)
    embed.add_field(name="👎 Downvotes", value="0", inline=True)

    approver_role_id = management_role_id if staff_mode else staff_role_id
    view = SuggestionView(author=user, approver_role_id=approver_role_id, staff_mode=staff_mode)
    msg = await channel.send(embed=embed, view=view)

    # ✅ Pass guild here!
    if log_channel:
        await log_suggestion("Created", user, suggestion, log_channel, guild)

    return msg


# ============================================================
# PREFIX COMMANDS
# ============================================================

# Public suggestion
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str = None):
    if not suggestion:
        embed = discord.Embed(
            title=f"{error_emoji} Missing Suggestion",
            description="Usage: `!suggest <your idea>`",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    msg = await post_suggestion(ctx.author, suggestion, ctx.guild, staff_mode=False)
    if msg:
        embed = discord.Embed(description=f"{tick_emoji} Your suggestion has been submitted!", color=discord.Color.green())
    else:
        embed = discord.Embed(description=f"{failed_emoji} Suggestion channel not found please open a support ticket.", color=discord.Color.red())
    await ctx.send(embed=embed)

# Staff suggestion
@bot.command(name="staff")
async def staff(ctx, subcommand: str = None, *, suggestion: str = None):
    staff_role = discord.utils.get(ctx.guild.roles, id=staff_role_id)
    if staff_role not in ctx.author.roles:
        embed = discord.Embed(description=f"{staff_emoji} You must be staff to use this.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if subcommand is None:
        embed = discord.Embed(
            title=f"{staff_emoji} Staff Command Help",
            description="Subcommands:\n`!staff suggest <idea>` — submit a staff suggestion.",
            color=0x1E77BE
        )
        await ctx.send(embed=embed)
        return

    if subcommand.lower() == "suggest":
        if not suggestion:
            embed = discord.Embed(
                title=f"{error_emoji} Missing Suggestion",
                description="Usage: `!staff suggest <idea>`",
                color=0x1E77BE
            )
            await ctx.send(embed=embed)
            return

        msg = await post_suggestion(ctx.author, suggestion, ctx.guild, staff_mode=True)
        if msg:
            embed = discord.Embed(description=f"{tick_emoji} Your staff suggestion has been submitted!", color=discord.Color.green())
        else:
            embed = discord.Embed(description=f"{failed_emoji} Suggestion channel not found please open a support ticket.", color=discord.Color.red())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title=f"{failed_emoji} Unknown Subcommand",
                              description=f"`{subcommand}` is not valid. Try `!staff suggest <idea>`.",
                              color=discord.Color.red())
        await ctx.send(embed=embed)

# ============================================================
# SLASH COMMANDS
# ============================================================

# Public
@bot.tree.command(name="suggest", description="Submit a public suggestion.")
async def suggest(interaction: discord.Interaction, suggestion: str):
    msg = await post_suggestion(interaction.user, suggestion, interaction.guild, staff_mode=False)
    if msg:
        embed = discord.Embed(description=f"{tick_emoji} Your suggestion has been submitted!", color=discord.Color.green())
    else:
        embed = discord.Embed(description=f"{failed_emoji} Suggestion channel not found please open a support ticket.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@staff_group.command(name="suggest", description="Submit a staff-only suggestion.")
async def staff_suggest(interaction: discord.Interaction, suggestion: str):
    staff_role = discord.utils.get(interaction.guild.roles, id=staff_role_id)
    if staff_role not in interaction.user.roles:
        embed = discord.Embed(description=f"{staff_emoji} You must be staff to use this.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    msg = await post_suggestion(interaction.user, suggestion, interaction.guild, staff_mode=True)
    if msg:
        embed = discord.Embed(description=f"{tick_emoji} Your staff suggestion has been submitted!", color=discord.Color.green())
    else:
        embed = discord.Embed(description=f"{failed_emoji} Suggestion channel not found please open a support ticket.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

#===

STAFF_FEEDBACK_CHANNEL_ID = 1343621982549311519  # 👈 staff-only feedback channel
STAFF_FEEDBACK_LOG_CHANNEL_ID = 1381267054354632745  # 👈 staff log channel

# ---------------- UTILITIES ----------------
async def send_feedback_embed(author: discord.User, target: discord.Member, feedback: str, guild: discord.Guild):
    # Prevent self-feedback
    if author.id == target.id:
        embed = discord.Embed(
            title=f"{error_emoji} Invalid Action",
            description="You can’t send feedback to yourself.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return embed

    # Check if target has the staff role
    staff_role = guild.get_role(staff_role_id)
    if not staff_role or staff_role not in target.roles:
        embed = discord.Embed(
            title=f"{error_emoji} Invalid Target",
            description=f"{target.mention} is not a staff member.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return embed

    # Channels
    staff_channel = bot.get_channel(STAFF_FEEDBACK_CHANNEL_ID)
    log_channel = bot.get_channel(STAFF_FEEDBACK_LOG_CHANNEL_ID)
    if not staff_channel:
        return discord.Embed(
            title=f"{failed_emoji} Error",
            description="Feedback channel not found. Please contact support.",
            color=discord.Color.red()
        )

    # Unix timestamp for time field
    timestamp = int(datetime.now(timezone.utc).timestamp())

    # Feedback embed for staff
    staff_embed = discord.Embed(
        title="💬 New Feedback Received",
        description=f"**Feedback:**\n```{feedback}```",
        color=0x1E77BE,
    )
    staff_embed.add_field(name="🧑‍💻 From", value=f"{author.mention} (`{author.id}`)", inline=False)
    staff_embed.add_field(name="🎯 To", value=f"{target.mention} (`{target.id}`)", inline=False)
    staff_embed.add_field(name=f"{time_emoji} Time", value=f"<t:{timestamp}:F>", inline=False)
    if guild and guild.icon:
        staff_embed.set_author(name=guild.name, icon_url=guild.icon.url)
    staff_embed.set_footer(text=f"Running {BOT_VERSION}")

    # Send to feedback channel and ping staff member
    await staff_channel.send(content=f"-# {ping_emoji} {target.mention}", embed=staff_embed)

    # Log embed for internal tracking
    if log_channel:
        log_embed = discord.Embed(
            title=f"{clipboard_emoji} Feedback Logged",
            color=0x1E77BE,
        )
        log_embed.add_field(name="🧑‍💻 From", value=f"{author.mention} (`{author.id}`)", inline=False)
        log_embed.add_field(name="🎯 To", value=f"{target.mention} (`{target.id}`)", inline=False)
        log_embed.add_field(name="💬 Feedback", value=f"```{feedback}```", inline=False)
        log_embed.add_field(name=f"{time_emoji} Time", value=f"<t:{timestamp}:F>", inline=False)
    if guild and guild.icon:
        log_embed.set_author(name=guild.name, icon_url=guild.icon.url)
        log_embed.set_footer(text=f"Running {BOT_VERSION}")
        await log_channel.send(embed=log_embed)

    # Confirmation embed to the sender
    confirm_embed = discord.Embed(
        title=F"{tick_emoji} Feedback Sent",
        description=f"Your feedback to {target.mention} has been sent to the staff channel.",
        color=discord.Color.green(),
    )
    if guild and guild.icon:
        confirm_embed.set_author(name=guild.name, icon_url=guild.icon.url)
    confirm_embed.set_footer(text=f"Running {BOT_VERSION}")
    return confirm_embed

# ---------------- PREFIX COMMAND ----------------
@bot.command(name="feedback")
async def feedback_prefix(ctx, to: discord.Member = None, *, feedback: str = None):
    # Ensure usage is correct
    if not to or not feedback:
        embed = discord.Embed(
            title="💡 Usage",
            description="# Use the command like this:\n`!feedback @staff <your message>`\n\nExample:\n`!feedback @Admin You're doing great!`",
            color=discord.Color.orange()
        )
        return await ctx.reply(embed=embed)

    # Send feedback
    embed = await send_feedback_embed(ctx.author, to, feedback, ctx.guild)
    await ctx.reply(embed=embed)

# ---------------- SLASH COMMAND ----------------
@bot.tree.command(name="feedback", description="Send feedback to a staff member.")
async def feedback_slash(interaction: discord.Interaction, to: discord.Member, feedback: str):
    await interaction.response.defer(ephemeral=True)
    embed = await send_feedback_embed(interaction.user, to, feedback, interaction.guild)
    await interaction.followup.send(embed=embed, ephemeral=True)

#--

# AFK storage: user_id -> {"reason": str, "set_time": datetime, "pings": [(channel_id, pinger_id, timestamp)]}
afk_users = {}

# ---------------- SET AFK ----------------
async def set_afk(user: discord.User, reason: str):
    afk_users[user.id] = {"reason": reason, "set_time": datetime.now(timezone.utc), "pings": []}
    
    embed = discord.Embed(
        description=f"{tick_emoji} I have set you as AFK for: **{reason}**" if reason else "I have set you as AFK.",
        color=discord.Color.orange()
    )
    return embed

# ---------------- COMMANDS ----------------
@bot.command(name="afk")
async def afk_prefix(ctx, *, reason: str = None):
    embed = await set_afk(ctx.author, reason)
    await ctx.send(embed=embed)

@bot.tree.command(name="afk", description="Set yourself as AFK")
async def afk_slash(interaction: discord.Interaction, reason: str = None):
    await interaction.response.defer(ephemeral=True)
    embed = await set_afk(interaction.user, reason)
    await interaction.followup.send(embed=embed, ephemeral=False)

# ---------------- AFK HANDLING ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Manual un-AFK
    if message.author.id in afk_users:
        afk_info = afk_users.pop(message.author.id)
        ping_lines = []
        for channel_id, pinger_id, ts in afk_info["pings"]:
            channel_link = f"<#{channel_id}>"
            pinger = bot.get_user(pinger_id)
            if pinger:
                ping_lines.append(f"-# {pinger.name} pinged you in {channel_link} at <t:{int(ts.timestamp())}:F>")
        if ping_lines:
            reply_text = f"{tick_emoji} Welcome back {message.author.mention}! You were pinged:\n" + "\n".join(ping_lines)
        else:
            reply_text = f"{tick_emoji} Welcome back {message.author.mention}!"
        await message.channel.send(reply_text)

    # Reply to AFK pings
    for user in message.mentions:
        if user.id in afk_users and user.id != message.author.id:
            afk_info = afk_users[user.id]
            afk_info["pings"].append((message.channel.id, message.author.id, datetime.now(timezone.utc)))
            reply_text = f"💤 {user.display_name} is currently AFK"
            if afk_info["reason"]:
                reply_text += f": {afk_info['reason']}"
            await message.channel.send(reply_text)

    await bot.process_commands(message)

#--

SERVER_ID = 1343179590247645205
WELCOME_CHANNEL_ID = 1343179590247645208
WELCOME_EMOJI = "<:SRPC:1345744266017636362>"

@bot.event
async def on_member_join(member: discord.Member):
    # Only send welcome messages if enabled
    if not welcome_status:
        return

    # Make sure it's the correct server
    if member.guild.id != SERVER_ID:
        return

    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    # Construct welcome message
    message = (
        f"Hello, {member.mention}! Welcome to {WELCOME_EMOJI} {member.guild.name}.\n"
        f"-# You're member {member.guild.member_count}."
    )

    await channel.send(message)

#---






#--

TOTAL_CHANNEL_ID = 1424779511588847616  # Voice channel for total members
HUMAN_CHANNEL_ID = 1424779529863303369  # Voice channel for human members
BOT_CHANNEL_ID = 1424779551342592131    # Voice channel for bots

# Prefixes (emojis or text)
total_vc_prefix = "👥 Total Members:"
human_vc_prefix = "🙎 Humans:"
bot_vc_prefix = "🤖 Bots:"

# === VC COUNTER TASK ===
@tasks.loop(seconds=600)  # Update every 10 minutes
async def update_member_count_vcs():
    """Updates the 3 VC names with member counts every few seconds."""
    try:
        guild = bot.get_guild(YOUR_GUILD_ID)
        if not guild:
            # print("[DEBUG] Guild not found.")
            return

        total_members = len(guild.members)
        bot_members = sum(1 for m in guild.members if m.bot)
        human_members = total_members - bot_members

        # print(f"[DEBUG] Updating VC counts → total={total_members}, humans={human_members}, bots={bot_members}")

        # Update only if the name changed
        await update_vc_name(guild, TOTAL_CHANNEL_ID, f"{total_vc_prefix} {total_members}")
        await asyncio.sleep(10)
        await update_vc_name(guild, HUMAN_CHANNEL_ID, f"{human_vc_prefix} {human_members}")
        await asyncio.sleep(10)
        await update_vc_name(guild, BOT_CHANNEL_ID, f"{bot_vc_prefix} {bot_members}")

    except discord.HTTPException as e:
        # print(f"[DEBUG] Failed to update VC names: {e}")
        return
    except Exception as e:
        # print(f"[DEBUG] Unexpected error in update_member_count_vcs: {e}")
        raise  # safer than pass, so errors still show in logs


async def update_vc_name(guild, channel_id, new_name):
    """Updates VC name only if it’s different."""
    channel = guild.get_channel(channel_id)
    if not channel or not isinstance(channel, discord.VoiceChannel):
        return
    if channel.name != new_name:
        # print(f"[DEBUG] Renaming {channel.name} → {new_name}")
        await channel.edit(name=new_name)


@update_member_count_vcs.before_loop
async def before_update_member_count_vcs():
    await bot.wait_until_ready()
    # print("[DEBUG] VC counter task started.")














failed_emoji_2 = "❌"
tick_emoji_2 = "✅"

# -------------------------------
# On command error: invalid command
# -------------------------------
@bot.event
async def on_command_error(ctx, error):
    """React with failed emoji if the command does not exist."""
    if isinstance(error, commands.CommandNotFound):
        try:
            await ctx.message.add_reaction(failed_emoji_2)
            await asyncio.sleep(0.25)
            await ctx.message.add_reaction("1️⃣")
        except discord.HTTPException:
            pass  # Ignore if bot can't react (no permission, etc.)
        return  # Prevent further error messages

    # Optional: handle other errors normally (e.g., missing permissions)
    raise error

@bot.command(name="send_test_message")
async def send_test_message(ctx):
    await ctx.send("<:failed:1387853598733369435> 1️⃣ = Command not found")










# --- Roblox User Lookup ---

@roblox_group.command(name="user", description="Get information about a Roblox user (username or user ID).")
@app_commands.describe(user="Enter a Roblox username or user ID.")
async def roblox_user(interaction: discord.Interaction, user: str):
    await interaction.response.defer(thinking=True)

    async def lookup_by_id(session: aiohttp.ClientSession, user_id: int):
        url = f"https://users.roblox.com/v1/users/{user_id}"
        async with session.get(url) as r:
            if r.status == 200:
                return await r.json()
            return None

    async def lookup_by_username(session: aiohttp.ClientSession, username: str):
        url = "https://users.roblox.com/v1/usernames/users"
        payload = {"usernames": [username], "excludeBannedUsers": False}
        async with session.post(url, json=payload) as r:
            if r.status == 200:
                data = await r.json()
                arr = data.get("data", [])
                if arr:
                    return arr[0]
            return None

    async with aiohttp.ClientSession() as session:
        try:
            user_obj = None

            # detect numeric user ID
            if user.isdigit():
                user_obj = await lookup_by_id(session, int(user))
                if not user_obj:
                    user_obj = await lookup_by_username(session, user)
            else:
                found = await lookup_by_username(session, user)
                if found:
                    user_obj = await lookup_by_id(session, found["id"])

            if not user_obj:
                embed = discord.Embed(
                    title=f"{failed_emoji_2} User Not Found",
                    description=f"Could not find a Roblox user for `{user}`.",
                    color=discord.Color.red(),
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)

            # extract info
            user_id = user_obj.get("id")
            username = user_obj.get("name")
            display_name = user_obj.get("displayName") or username
            description = user_obj.get("description") or "None"
            created = user_obj.get("created")
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"

            # --- created date fix ---
            created_dt = None
            if created:
                try:
                    # Normalize Z → +00:00 and handle milliseconds
                    clean = created.replace("Z", "+00:00")
                    if "." in clean:
                        clean = clean.split(".")[0] + "+00:00"
                    created_dt = datetime.datetime.fromisoformat(clean)
                except Exception:
                    created_dt = None

            # fetch avatar
            avatar_url = None
            thumb_url = (
                f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
                f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            )
            async with session.get(thumb_url) as tr:
                if tr.status == 200:
                    td = await tr.json()
                    data = td.get("data")
                    if data and isinstance(data, list) and data[0].get("imageUrl"):
                        avatar_url = data[0]["imageUrl"]

            # --- build embed ---
            embed = discord.Embed(
                title=f"{display_name}",
                color=0x1E77BE,
                url=profile_url,
                description=f"""
> 🧾 **Name:** [@{username}]({profile_url}) ({display_name})
> 🆔 **ID:** `{user_id}`
> 🗒️ **Description:** {description}
                """,
            )

            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            embed.set_footer(text=f"Running {BOT_VERSION}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title=f"{failed_emoji_2} Roblox API Error",
                description=f"An error occurred while fetching data:\n`{e}`",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)






async def handle_roblox_user(ctx, roblox_user: str):
    async with ctx.typing():  # ← correct typing context
        async def lookup_by_id(session: aiohttp.ClientSession, user_id: int):
            url = f"https://users.roblox.com/v1/users/{user_id}"
            async with session.get(url) as r:
                if r.status == 200:
                    return await r.json()
                return None

        async def lookup_by_username(session: aiohttp.ClientSession, username: str):
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": False}
            async with session.post(url, json=payload) as r:
                if r.status == 200:
                    data = await r.json()
                    arr = data.get("data", [])
                    if arr:
                        return arr[0]
                return None

        async with aiohttp.ClientSession() as session:
            try:
                user_obj = None

                if roblox_user.isdigit():
                    user_obj = await lookup_by_id(session, int(roblox_user))
                    if not user_obj:
                        user_obj = await lookup_by_username(session, roblox_user)
                else:
                    found = await lookup_by_username(session, roblox_user)
                    if found:
                        user_obj = await lookup_by_id(session, found["id"])

                if not user_obj:
                    embed = discord.Embed(
                        title=f"{failed_emoji_2} User Not Found",
                        description=f"Could not find a Roblox user for `{roblox_user}`.",
                        color=discord.Color.red(),
                    )
                    return await ctx.send(embed=embed)

                user_id = user_obj.get("id")
                username = user_obj.get("name")
                display_name = user_obj.get("displayName") or username
                description = user_obj.get("description") or "None"
                profile_url = f"https://www.roblox.com/users/{user_id}/profile"

                # Fetch avatar
                avatar_url = None
                thumb_url = (
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
                    f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
                )
                async with session.get(thumb_url) as tr:
                    if tr.status == 200:
                        td = await tr.json()
                        data = td.get("data")
                        if data and isinstance(data, list) and data[0].get("imageUrl"):
                            avatar_url = data[0]["imageUrl"]

                embed = discord.Embed(
                    title=f"{display_name}",
                    color=0x1E77BE,
                    url=profile_url,
                    description=f"""
> 🧾 **Name:** [@{username}]({profile_url}) ({display_name})
> 🆔 **ID:** `{user_id}`
> 🗒️ **Description:** {description}
                    """,
                )

                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)

                embed.set_footer(text=f"Running {BOT_VERSION}")
                await ctx.send(embed=embed)

            except Exception as e:
                embed = discord.Embed(
                    title=f"{failed_emoji_2} Roblox API Error",
                    description=f"An error occurred while fetching data:\n`{e}`",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)


@bot.command(name="roblox")
async def roblox(ctx, subcommand: str = None, roblox_user: str = None):
    if not subcommand:
        return await ctx.send("❌ Unknown command. Use `!roblox user <username_or_id>`.")

    subcommand = subcommand.lower()
    handlers = {
        "user": handle_roblox_user,
    }

    handler = handlers.get(subcommand)
    if not handler:
        return await ctx.send(f"❌ Unknown subcommand `{subcommand}`. Use `!roblox user <username_or_id>`.")

    if subcommand == "user":
        if not roblox_user:
            return await ctx.send("❌ Please provide a username or user ID for the `user` subcommand.")
        await handler(ctx, roblox_user=roblox_user)











async def send_owner_bypass_embed(interaction: discord.Interaction, reason: str = "Bypassing checks..."):
    """
    Sends a public 'Owner Bypass Activated' embed and returns the sent message.
    This can then be edited later with logs, results, etc.
    """
    embed = discord.Embed(
        description=f"⏳ {reason}",
        colour=discord.Color.gold()
    )

    # Send public (non-ephemeral) message and return it for editing
    await interaction.response.send_message(embed=embed)
    return await interaction.original_response()



@erlc_group.command(name="joins", description="View ER:LC join/leave logs (staff only, owner bypass)")
async def erlc_joins(interaction: discord.Interaction):
    user = interaction.user
    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    # --- Permission Check ---
    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Colour.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # --- Owner Bypass Path ---
    if is_owner and not has_staff_role:
        # Send bypass embed first
        bypass_message = await send_owner_bypass_embed(interaction, reason="Bypassing checks...")
        await asyncio.sleep(1.5)
    else:
        # Regular staff use: show "thinking" indicator
        await interaction.response.defer(thinking=True)
        bypass_message = None

    try:
        # Fetch join/leave logs
        join_logs = await fetch_api_data(f"{API_BASE}/joinlogs")

        if not join_logs:
            description = "> There are no recent join/leave logs."
            count = 0
        else:
            entries = []
            for entry in join_logs:
                player_str = entry.get("Player", "Unknown:0")
                timestamp = entry.get("Timestamp", 0)
                joined = entry.get("Join", True)  # True = joined, False = left

                username, player_id = parse_player(player_str)
                user_link = f"[{username}](https://www.roblox.com/users/{player_id}/profile)" if player_id else username

                if joined:
                    entries.append(f"> {user_link} joined the server <t:{timestamp}:R>")
                else:
                    entries.append(f"> {user_link} left the server <t:{timestamp}:R>")

            count = len(entries)
            description = "\n".join(entries)

        # Create embed
        embed = discord.Embed(
            title=f"ER:LC Join/Leave Logs ({count})",
            description=description,
            colour=0x1E77BE
        )

        guild = interaction.guild
        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
            embed.set_footer(text=f"Running {BOT_VERSION}")

        # Edit owner embed or send normally
        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await interaction.followup.send(embed=embed)

    except Exception as e:
        # Handle error gracefully
        err_msg = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(
            title="❌ ERLC API Error",
            description=err_msg,
            colour=discord.Color.red()
        )
        error_embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=error_embed)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)



















@erlc_group.command(name="modcalls", description="View ER:LC moderator call logs (staff only, owner bypass)")
async def erlc_modcalls(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild

    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    # --- Permission Check ---
    if not has_staff_role and not is_owner:
        embed = discord.Embed(
            title="Permission Denied",
            description="❌ You do not have permission to use this command.",
            colour=discord.Colour.red()
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # --- Owner Bypass Path ---
    if is_owner and not has_staff_role:
        # Send bypass embed first
        bypass_message = await send_owner_bypass_embed(interaction, reason="Bypassing checks...")
        await asyncio.sleep(1.5)
    else:
        # Regular staff use: show "thinking" indicator
        await interaction.response.defer(thinking=True)
        bypass_message = None

    try:
        # Fetch mod call logs
        modcalls = await fetch_api_data(f"{API_BASE}/modcalls")

        if not modcalls:
            description = "> There are no recent moderator call logs."
            count = 0
        else:
            entries = []
            for entry in modcalls:
                caller_str = entry.get("Caller", "Unknown:0")
                moderator_str = entry.get("Moderator", None)
                timestamp = entry.get("Timestamp", 0)

                caller_name, caller_id = parse_player(caller_str)
                caller_link = f"[{caller_name}](https://www.roblox.com/users/{caller_id}/profile)" if caller_id else caller_name

                if moderator_str:
                    mod_name, mod_id = parse_player(moderator_str)
                    mod_link = f"[{mod_name}](https://www.roblox.com/users/{mod_id}/profile)" if mod_id else mod_name
                    entries.append(f"> {caller_link} called for a mod <t:{timestamp}:R>, handled by {mod_link}")
                else:
                    entries.append(f"> {caller_link} called for a mod <t:{timestamp}:R> (unanswered)")

            count = len(entries)
            description = "\n".join(entries)

        # Create embed
        embed = discord.Embed(
            title=f"ER:LC ModCall Logs ({count})",
            description=description,
            colour=0x1E77BE
        )

        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        # Edit bypass message or send normally
        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await interaction.followup.send(embed=embed)

    except Exception as e:
        err_msg = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(
            title="❌ ERLC API Error",
            description=err_msg,
            colour=discord.Color.red()
        )
        error_embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=error_embed)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)












# --- Helper: Resolve Roblox username to profile link ---
async def resolve_roblox_owner_link(owner_name: str) -> str:
    """
    Returns a clickable Roblox profile link for the given username.
    Tries to fetch the user ID from Roblox API. Falls back to a search link.
    """
    if not owner_name:
        return "Unknown"

    # Encode username for URL
    safe_name = urllib.parse.quote(owner_name)
    api_url = f"https://users.roblox.com/v1/users/search?keyword={safe_name}&limit=1"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    users = data.get("data", [])
                    if users:
                        uid = users[0].get("id")
                        uname = users[0].get("name")
                        if uid and uname:
                            return f"[{uname}](https://www.roblox.com/users/{uid}/profile)"
    except Exception:
        pass

    # Fallback: generic search link
    return f"[{owner_name}](https://www.roblox.com/users/search?keyword={safe_name})"



# ------------------------------
# Slash command: /erlc vehicles
# ------------------------------
@erlc_group.command(name="vehicles", description="View spawned vehicles (staff only, owner bypass)")
async def erlc_vehicles(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild
    has_staff_role = any(r.id == staff_role_id for r in getattr(user, "roles", []))
    is_owner = user.id == owner_id

    if not has_staff_role and not is_owner:
        embed = discord.Embed(title="Permission Denied",
                              description="❌ You do not have permission to use this command.",
                              colour=discord.Colour.red())
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # --- Owner Bypass Path ---
    if is_owner and not has_staff_role:
        # Send bypass embed first
        bypass_message = await send_owner_bypass_embed(interaction, reason="Bypassing checks...")
        await asyncio.sleep(1.5)
    else:
        # Regular staff use: show "thinking" indicator
        await interaction.response.defer(thinking=True)
        bypass_message = None

    try:
        vehicles = await fetch_api_data(f"{API_BASE}/vehicles")

        if not vehicles:
            description = "> There are no spawned vehicles in the server."
            count = 0
        else:
            lines = []
            for v in vehicles:
                name = v.get("Name", "Unknown Vehicle")
                texture = v.get("Texture", "Unknown")
                owner_raw = v.get("Owner", "")  # e.g. "flat_bird"

                # Try to resolve owner to a Discord mention if possible
                owner_display = await resolve_roblox_owner_link(owner_raw)

                # Example line: > **2019 Falcon** — `Standard` (Owner: <@1234> / flat_bird)
                lines.append(f"> **{name}** — `{texture}` (Owner: {owner_display})")

            count = len(lines)
            description = "\n".join(lines)

        embed = discord.Embed(title=f"ER:LC Vehicles ({count})", description=description, colour=0x1E77BE)
        if guild:
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        if bypass_message:
            await bypass_message.edit(embed=embed)
        else:
            await interaction.followup.send(embed=embed)

    except Exception as e:
        err_msg = get_erlc_error_message(0, exception=e)
        error_embed = discord.Embed(title="❌ ERLC API Error", description=err_msg, colour=discord.Color.red())
        error_embed.set_footer(text=f"Running {BOT_VERSION}")
        if bypass_message:
            await bypass_message.edit(embed=error_embed)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)




































































































































# ---------------------- commmand info ----------------------

command_categories = {
    "🛠️ General": [
        ("ping", "Check if the bot is online"),
        ("uptime", "Check the bots uptime"),
        ("Sync", "Sync slash commands owner only + prefix only"),
        ("servers", "owner only see all servers that the bots in"),
        ("help", "show info about a command"),
        ("commands", "show all commands"),
        ("feedback", "Send feedback to a staff member"),
        ("suggest", "Submit a public suggestion"),
        ("staff suggest", "Submit a staff-only suggestion"),
        ("afk", "Set yourself as AFK")
    ],
    "⚙️ Moderation": [
        ("N/A", "N/A")
    ],
    "🚨 ER:LC": [
        ("erlc command", "Send a command to the erlc server"),
        ("erlc kills", "Show killlogs from the server"),
        ("erlc players", "Show players in game"),
        ("discord check", "Check whos in the discord and whos not"),
        ("erlc info", "Give erlc info from the server"),
        ("erlc code", "Show the erlc code"),
        ("erlc bans", "Vuew all baned players from in-game."),
        ("erlc teamkick", "kick a player off team."),
        ("erlc logs", "Show in-game command logs"),
        ("erlc joins", "View ER:LC join/leave logs (staff only, owner bypass)"),
        ("erlc modcalls", "View ER:LC moderator call logs (staff only, owner bypass)"),
        ("erlc vehicles", "View spawned vehicles (staff only, owner bypass)")
    ],
    "🔒 Channel Management": [
        ("N/A", "N/A")
    ],
    "💼 Owner Commands": [
        ("joincode", "Update join code VC."),
        ("servername", "Update server name VC."),
        ("sync", "Sync all / commands.")

    ]
}

# ---------------------- .commands ----------------------

@bot.command(name="commands", description="Show all available commands")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="Bot Commands List",
        description=f"Explore the available commands grouped by category. Use `{COMMAND_PREFIX}help [command name]` or `/help [command name]` for more details.",
        color=0x1E77BE
    )

    for category, commands_list in command_categories.items():
        field_text = ", ".join(f"`{cmd}`" for cmd, _ in commands_list)
        embed.add_field(name=f"**{category}**", value=field_text, inline=False)

    # Set consistent author & footer
    embed.set_footer(text=f"Running {BOT_VERSION}")
    embed.set_author(
        name=ctx.guild.name if ctx.guild else "Bot",
        icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None,
    )

    await ctx.send(embed=embed)

# ---------------------- /commands ----------------------

@bot.tree.command(name="commands", description="Show all available commands")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands List",
        description=f"Explore the available commands grouped by category. Use `{COMMAND_PREFIX}help [command name]` or `/help [command name]` for more details.",
        color=0x1E77BE
    )

    for category, commands_list in command_categories.items():
        field_text = "\n".join(f"/{cmd} - {desc}" for cmd, desc in commands_list)
        embed.add_field(name=f"**{category}**", value=field_text, inline=False)

    # Set consistent author & footer
    embed.set_footer(text=f"Running {BOT_VERSION}")
    embed.set_author(
        name=interaction.guild.name if interaction.guild else "Bot",
        icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
    )

    await interaction.response.send_message(embed=embed)

# ---------------------- .help for command ----------------------

@bot.command(name="help", description="Get detailed help for a specific command")
async def command_help_prefix(ctx, command: str = None):
    if not command:
        embed = discord.Embed(
            title=f"{failed_emoji} Error",
            description="You must specify a command to get help for. Example:\n`.help ping`",
            color=ERROR_COLOR
        )
        # React to the user's message with the failed emoji
        try:
            await ctx.message.add_reaction(failed_emoji)
        except (discord.errors.HTTPException, discord.errors.Forbidden) as e:
            # Optionally log the error
            print(f"Failed to add reaction: {e}")
        
        await ctx.send(embed=embed)
        return

    await send_command_detail(ctx, command)

# ---------------------- /help for command ----------------------

@bot.tree.command(name="help", description="Get detailed help for a specific command")
@app_commands.describe(command="The command to get help for")
async def command_help_slash(interaction: discord.Interaction, command: str):
    await send_command_detail(interaction, command)

# ---------------------- help data ----------------------

# All commands and their details in one dict
command_details = {
    "ping": {
        "description": "Check if the bot is online.",
        "usage": f"`{COMMAND_PREFIX}ping` or `/ping`"
    },
    "commands": {
        "description": "List all available commands.",
        "usage": f"`{COMMAND_PREFIX}commands` or `/commands`"
    },
    "help": {
        "description": "Get detailed help for a specific command.",
        "usage": f"`{COMMAND_PREFIX}help [command]` or `/help [command]`"
    },
    "uptime": {
        "description": "Show how long the bot has been running.",
        "usage": f"`{COMMAND_PREFIX}uptime` or `/uptime`"
    },
    "erlc command": {
        "description": "Send a command to the server.",
        "useage": f"`{COMMAND_PREFIX}erlc command` or `/erlc command [command]`"
    },
    "erlc kills": {
        "description": "Get all killlogs from the erlc server.",
        "useage": f"`{COMMAND_PREFIX}erlc kills` or `/erlc kills`"
    },
    "erlc players": {
        "description": "Show all players in game",
        "useage": f"`{COMMAND_PREFIX}erlc players` or `/erlc players`"
    },
        "discord check": {
        "description": "Show whos in the Discord server and whos not.",
        "useage": f"`{COMMAND_PREFIX}discord check` or `/discord check`"
    },
        "erlc info": {
        "description": "Show erlc info from the server.",
        "useage": f"`{COMMAND_PREFIX}erlc info` or `/erlc info`"
    },
        "erlc code": {
        "description": "Show the erlc server code.",
        "useage": f"`{COMMAND_PREFIX}erlc code` or `/erlc code`"
    },
        "servers": {
        "description": "Show all servers that the bots in",
        "useage": f"`{COMMAND_PREFIX}servers` or `/servers`"
    },
        "sync": {
        "description": "Sync all commands.",
        "useage": f"`{COMMAND_PREFIX}sync`"
    },
        "joincode": {
        "description": "Sync the VC channel that has the join code on it.",
        "useage": f"`{COMMAND_PREFIX}joincode`"
    },
        "servername": {
        "description": "Sync the VC channel that has the server name on it.",
        "useage": f"`{COMMAND_PREFIX}servername`"
    },
        "erlc bans": {
        "description": "View all baned players in-game.",
        "useage": f"`{COMMAND_PREFIX}erlc bans` or `/erlc bans`"
    },
        "erlc teamkick": {
        "description": "Kick a player from any team that needs you not to be wanted.",
        "useage": f"`{COMMAND_PREFIX}erlc teamkick [player] [reason]` or `/erlc teamkick [player] [reason]`"
    },
        "erlc logs": {
        "description": "Show in-game command logs.",
        "useage": f"`{COMMAND_PREFIX}erlc logs` or `/erlc logs`"
    },
        "feedback": {
        "description": "Send feedback to a staff member.",
        "useage": f"`{COMMAND_PREFIX}feedback [@staff] [message]` or `/feedback [@staff] [message]`"
    },
        "suggest": {
        "description": "Submit a public suggestion.",
        "useage": f"`{COMMAND_PREFIX}suggest [your idea]` or `/suggest [your idea]`"
    },
        "staff suggest": {
        "description": "Submit a staff-only suggestion.",
        "useage": f"`{COMMAND_PREFIX}staff suggest [your idea]` or `/staff suggest [your idea]`"
    },
        "afk": {
        "description": "Set yourself as AFK.",
        "useage": f"`{COMMAND_PREFIX}afk [reason]` or `/afk [reason]`"
    },
        "erlc joins": {
        "description": "View ER:LC join/leave logs (staff only, owner bypass).",
        "useage": f"`{COMMAND_PREFIX}erlc joins` or `/erlc joins`"
    },
        "erlc modcalls": {
        "description": "View ER:LC moderator call logs (staff only, owner bypass).",
        "useage": f"`{COMMAND_PREFIX}erlc modcalls` or `/erlc modcalls`"
    },
        "erlc vehicles": {
        "description": "View spawned vehicles (staff only, owner bypass).",
        "useage": f"`{COMMAND_PREFIX}erlc vehicles` or `/erlc vehicles`"
    }
}

# ---------------------- helper for help command ----------------------

# Updated helper function
async def send_command_detail(target, command_name):
    command_name = command_name.lower()
    matching = [name for name in command_details if command_name in name]

    if len(matching) == 1:
        cmd = matching[0]
        data = command_details[cmd]
        embed = discord.Embed(
            title=f"Help: /{cmd}",
            description=f"**Description:** {data['description']}\n**Usage:** {data['usage']}",
            color=0x1E77BE
        )
        if isinstance(target, commands.Context):
            await target.send(embed=embed)
        else:
            await target.response.send_message(embed=embed)
    elif len(matching) > 1:
        message = f"Multiple matches found: {', '.join(matching)}."
        if isinstance(target, commands.Context):
            await target.send(message)
        else:
            await target.response.send_message(message)
    else:
        message = f"No help found for `{command_name}`."
        if isinstance(target, commands.Context):
            await target.send(message)
        else:
            await target.response.send_message(message)

# ========================= Run the bot =========================

if __name__ == "__main__":
    try:
        token = os.getenv("DISCORD_TOKEN_BATA")
        if not token:
            raise ValueError("⚠️ DISCORD_TOKEN is missing from environment variables.")

        bot.run(token)

    except ValueError as ve:
        print(f"[Config Error] {ve}")
    except discord.LoginFailure:
        print("❌ Invalid Discord token provided. Please check your DISCORD_TOKEN.")
    except discord.HTTPException as http_ex:
        print(f"⚠️ Discord HTTP error: {http_ex}")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped manually (KeyboardInterrupt).")
    except Exception as e:
        print(f"🔥 Unexpected error occurred: {e}")