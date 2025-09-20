# ========================= Import =========================

import discord
import random
import string
import datetime
import traceback
import json
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


# ========================= Helpers =========================

# Prefix for commands
COMMAND_PREFIX = "."
# version
BOT_VERSION = "v1.0.0"

# ========================= Other =========================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


# ========================= Bot on_ready =========================

@bot.event
async def on_ready():
    try:
        # Register groups BEFORE syncing
        bot.tree.add_command(erlc_group)
        bot.tree.add_command(discord_group)

        # Global sync
        await bot.tree.sync()

        # Guild-specific sync (optional — only if you want instant updates in test guild)
        await bot.tree.sync(guild=discord.Object(id=1299000909363155024))

    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    bot.start_time = datetime.now(timezone.utc)

    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()

    # Start background tasks
    try:
        join_leave_log_task.start()
        kill_log_task.start()
        modcall_log_task.start()
        team_join_leave_log_task.start()
    except Exception as e:
        print(f"⚠️ Error starting background tasks: {e}")

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    print(f"{bot.user}({bot.user.id}) has connected to Discord and is watching over the server.")
    print("-----------------------------------------------------------------------")

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

def is_staff_or_owner():
    async def predicate(interaction: discord.Interaction):
        # Owner always passes
        if interaction.user.id == owner_id:
            return True
        # Staff role check
        if interaction.guild and any(r.id == staff_role_id for r in interaction.user.roles):
            return True
        return False
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

@bot.command(name="ping")
async def ping_prefix(ctx: commands.Context):
    latency = round(bot.latency * 1000)
    uptime_str = get_uptime(bot)

    embed = discord.Embed(
        title=f"{pong_emoji} Pong!",
        description=(
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"> Version: `{BOT_VERSION}`\n"
        ),
        color=discord.Color(0x1E77BE)
    )

    embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await ctx.send(embed=embed)


# ---------------------- /PING ----------------------

@bot.tree.command(name="ping", description="Check the bot's latency and uptime")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    uptime_str = get_uptime(bot)

    embed = discord.Embed(
        title=f"{pong_emoji} Pong!",
        description=(
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"> Version: `{BOT_VERSION}`\n"
        ),
        color=discord.Color(0x1E77BE)
    )

    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await interaction.response.send_message(embed=embed)

# ---------------------- .uptime ----------------------

@bot.command(name="uptime")
async def uptime_prefix(ctx: commands.Context):
    uptime_str = get_uptime(bot)

    embed = discord.Embed(
        title=f"{time_emoji} Bot Uptime",
        description=f"The bot has been online for:\n**{uptime_str}**",
        color=discord.Color(0x1E77BE)
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
        color=discord.Color(0x1E77BE)
    )

    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    await interaction.response.send_message(embed=embed)

# ---------------------- .servers ----------------------

@bot.command(name="servers")
@commands.is_owner()
async def servers(ctx: commands.Context):
    # List all servers the bot is in.
    await ctx.defer()
    guilds = bot.guilds
    if not guilds:
        await ctx.send("The bot is not in any servers.")
        return

    for guild in guilds:
        owner = guild.owner
        invite_link = "No invite available"
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                try:
                    invite = await channel.create_invite(max_age=3600, max_uses=1, unique=True)
                    invite_link = invite.url
                    break
                except (discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    print(f"Failed to create invite for guild {guild.name}: {e}")
                    # Keep invite_link as "No invite available"
        
        embed = discord.Embed(
            title=guild.name,
            description=f"ID: `{guild.id}`\nOwner: {owner}\nMembers: {guild.member_count}\nInvite: {invite_link}",
            color=discord.Color(0x1E77BE)
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await ctx.send(embed=embed)

# ---------------------- /servers ----------------------

@bot.tree.command(name="servers", description="List all servers the bot is in")
@is_owner()
async def servers(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guilds = bot.guilds
    if not guilds:
        await interaction.followup.send("The bot is not in any servers.")
        return

    for guild in guilds:
        owner = guild.owner
        invite_link = "No invite available"

        # Attempt to create an invite for the first available text channel
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
            description=f"ID: `{guild.id}`\nOwner: {owner}\nMembers: {guild.member_count}\nInvite: {invite_link}",
            color=discord.Color(0x1E77BE)
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")

        await interaction.followup.send(embed=embed, ephemeral=True)

# ---------------------- .sync ----------------------

@bot.command(name="sync")
async def sync(ctx):
    """Owner-only: !sync"""
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ You are not authorized to use this command.")

    try:
        async with ctx.typing():
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} application command(s).")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: `{e}`")
        print(f"[ERROR] !sync failed: {e}")

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

# ---------------------- join/leave logs ----------------------

@tasks.loop(seconds=60)
async def join_leave_log_task():
    global session
    if not session:
        session = aiohttp.ClientSession()

    try:
        async with session.get(f"{API_BASE}/joinlogs", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
                print(f"Failed to fetch join logs: {resp.status}")
                return
            data = await resp.json()
    except Exception as e:
        print(f"Error fetching join logs: {e}")
        return

    if not data:
        return

    # Get the channel (from cache or API)
    channel = bot.get_channel(JOIN_LEAVE_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(JOIN_LEAVE_LOG_CHANNEL_ID)
        except Exception as e:
            print(f"Failed to fetch join/leave log channel: {e}")
            return

    if not hasattr(join_leave_log_task, "last_ts"):
        join_leave_log_task.last_ts = 0

    join_events, leave_events = [], []

    for entry in data:
        ts = entry.get("Timestamp", 0)
        if ts <= join_leave_log_task.last_ts:
            continue

        player_str = entry.get("Player", "Unknown:0")
        joined = entry.get("Join", True)

        # Parse username and Roblox ID
        try:
            username, id_str = player_str.split(":", 1)
            player_id = int(id_str)
        except (ValueError, AttributeError):
            username = player_str
            player_id = 0

        user_link = (
            f"[{username}](https://www.roblox.com/users/{player_id}/profile)"
            if player_id
            else username
        )

        if joined:
            join_events.append(f"{user_link} joined at <t:{ts}:F>")
        else:
            leave_events.append(f"{user_link} left at <t:{ts}:F>")

        # Update last timestamp
        join_leave_log_task.last_ts = max(join_leave_log_task.last_ts, ts)

    # Send a single embed for all joins
    if join_events:
        embed = discord.Embed(
            title="Join Log",
            description="\n".join(join_events),
            colour=0x00f529
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await channel.send(embed=embed)

    # Send a single embed for all leaves
    if leave_events:
        embed = discord.Embed(
            title="Leave Log",
            description="\n".join(leave_events),
            colour=0xf50000
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await channel.send(embed=embed)

# ---------------------- kill logs ----------------------

@tasks.loop(seconds=60)
async def kill_log_task():
    global session
    if not session:
        session = aiohttp.ClientSession()

    # Fetch kill logs
    try:
        async with session.get(f"{API_BASE}/killlogs", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
                print(f"Failed to fetch kill logs: {resp.status}")
                return
            data = await resp.json()
    except Exception as e:
        print(f"Error fetching kill logs: {e}")
        return

    if not data:
        return

    # Get Discord channel
    channel = bot.get_channel(KILL_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(KILL_LOG_CHANNEL_ID)
        except Exception as e:
            print(f"Failed to fetch kill log channel: {e}")
            return

    if not hasattr(kill_log_task, "last_ts"):
        kill_log_task.last_ts = 0

    kill_events = []

    for entry in data:
        ts = entry.get("Timestamp", 0)
        if ts <= kill_log_task.last_ts:
            continue

        # Split "Username:UserId"
        killer_raw = entry.get("Killer", "Unknown:0")
        victim_raw = entry.get("Killed", "Unknown:0")

        if ":" in killer_raw:
            killer_name, killer_id = killer_raw.split(":", 1)
        else:
            killer_name, killer_id = killer_raw, "0"

        if ":" in victim_raw:
            victim_name, victim_id = victim_raw.split(":", 1)
        else:
            victim_name, victim_id = victim_raw, "0"

        # Build Roblox profile links if ID is valid
        killer_link = (
            f"[{killer_name}](https://www.roblox.com/users/{killer_id}/profile)"
            if killer_id != "0" else killer_name
        )
        victim_link = (
            f"[{victim_name}](https://www.roblox.com/users/{victim_id}/profile)"
            if victim_id != "0" else victim_name
        )

        kill_events.append(f"{killer_link} killed {victim_link} at <t:{ts}:F>")

        # Update last timestamp
        kill_log_task.last_ts = max(kill_log_task.last_ts, ts)

    # Send all kills in one embed
    if kill_events:
        embed = discord.Embed(
            title="Kill Log",
            description="\n".join(kill_events),
            colour=0xffa200
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await channel.send(embed=embed)

# ---------------------- mocall logs ----------------------

@tasks.loop(seconds=60)
async def modcall_log_task():
    global session
    if not session:
        session = aiohttp.ClientSession()

    try:
        async with session.get(f"{API_BASE}/modcalls", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
                print(f"Failed to fetch modcall logs: {resp.status}")
                return
            data = await resp.json()
    except Exception as e:
        print(f"Error fetching modcall logs: {e}")
        return

    if not data:
        return

    channel = bot.get_channel(MODCALL_LOG_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(MODCALL_LOG_CHANNEL_ID)
        except Exception as e:
            print(f"Failed to fetch modcall log channel: {e}")
            return

    if not hasattr(modcall_log_task, "last_ts"):
        modcall_log_task.last_ts = 0

    modcall_events = []

    for entry in data:
        ts = int(entry.get("Timestamp", 0))
        if ts <= modcall_log_task.last_ts:
            continue

        # Caller
        caller_raw = entry.get("Caller", "Unknown:0")
        try:
            caller_name, caller_id_str = caller_raw.split(":", 1)
            caller_id = int(caller_id_str)
        except (ValueError, AttributeError):
            caller_name, caller_id = caller_raw, 0

        # Moderator (responder) — may be missing if not yet taken
        moderator_raw = entry.get("Moderator")
        if moderator_raw:
            try:
                mod_name, mod_id_str = moderator_raw.split(":", 1)
                mod_id = int(mod_id_str)
            except (ValueError, AttributeError):
                mod_name, mod_id = moderator_raw, 0
        else:
            mod_name, mod_id = "Unassigned", 0

        caller_link = (
            f"[{caller_name}](https://www.roblox.com/users/{caller_id}/profile)"
            if caller_id else caller_name
        )
        moderator_link = (
            f"[{mod_name}](https://www.roblox.com/users/{mod_id}/profile)"
            if mod_id else mod_name
        )

        modcall_events.append(
            f"{moderator_link} responded to {caller_link} at <t:{ts}:F>"
        )

        modcall_log_task.last_ts = max(modcall_log_task.last_ts, ts)

    # Send all new modcalls in one embed
    if modcall_events:
        embed = discord.Embed(
            title="Modcall Log",
            description="\n".join(modcall_events),
            colour=0xe1ff00
        )
        embed.set_footer(text=f"Running {BOT_VERSION}")
        await channel.send(embed=embed)

# ---------------------- team join/leave logs ----------------------

@tasks.loop(seconds=60)
async def team_join_leave_log_task():
    global session
    if not session:
        session = aiohttp.ClientSession()

    players = await fetch_players()
    if not players:
        return

    channel = await get_team_log_channel()
    if not channel:
        return

    if not hasattr(team_join_leave_log_task, "last_team_state"):
        team_join_leave_log_task.last_team_state = {}

    join_events, leave_events = compute_team_changes(players, team_join_leave_log_task.last_team_state)

    await send_log_embed(channel, "Team Join Log", join_events)
    await send_log_embed(channel, "Team Leave Log", leave_events)


# --- Helper Functions ---

async def fetch_players():
    try:
        async with session.get(f"{API_BASE}/players", headers={"server-key": API_KEY}) as resp:
            if resp.status != 200:
                print(f"Failed to fetch players: {resp.status}")
                return []
            return await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Error fetching players: {e}")
        return []


async def get_team_log_channel():
    channel = bot.get_channel(TEAM_JOIN_LEAVE_LOG_CHANNEL_ID)
    if channel:
        return channel
    try:
        return await bot.fetch_channel(TEAM_JOIN_LEAVE_LOG_CHANNEL_ID)
    except discord.DiscordException as e:
        print(f"Failed to fetch team log channel: {e}")
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


async def send_log_embed(channel, title, events):
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

def get_erlc_error_message(http_status: int, api_code: str = None, exception: Exception = None) -> str:
    """
    Returns a formatted error message with optional API code or exception details.
    """
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

    # If exception exists but status is 0, just show exception
    if http_status == 0 and exception:
        return f"{error_emoji} **Unhandled Exception**:\n`{str(exception)}`"

    base_message = messages.get(
        http_status,
        f"{error_emoji} **{http_status} – Unknown Error**: An unexpected error occurred."
    )

    if api_code:
        base_message += f"\nAPI Code: `{api_code}`"
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
        color=discord.Color(0x1E77BE),
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

# ---------------------- all players in the discord server embed for /discord check  ----------------------

def all_players_in_discord_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="Discord Check",
        description=f"{tick_emoji} All players are in the Discord!",
        color=discord.Color(0x1E77BE),
    )
    embed.set_author(name=guild.name, icon_url=guild.icon.url)
    embed.set_footer(text=f"Running {BOT_VERSION}")
    return embed

# ---------------------- main code for /discord check ----------------------

async def fetch_discord_check_embed(guild: discord.Guild) -> discord.Embed:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"server-key": API_KEY}
            async with session.get(f"{API_BASE}/players", headers=headers) as res:
                if res.status == 422:
                    # No players → return "All in Discord" embed
                    return all_players_in_discord_embed(guild)

                if res.status != 200:
                    # Other errors → raise
                    raise Exception(await res.text())

                data = await res.json()
                players = [p["Player"].split(":")[0] for p in data]

        # Compare with Discord members
        guild_members = [m.display_name for m in guild.members] + [m.name for m in guild.members]
        not_in_discord = []
        for roblox_name in players:
            pattern = re.compile(rf"\b{re.escape(roblox_name)}\b", re.IGNORECASE)
            if not any(pattern.search(name) for name in guild_members):
                not_in_discord.append(roblox_name)

        # Build embed
        if not_in_discord:
            formatted = "\n".join(
                [f"[{u}](https://www.roblox.com/users/profile?username={u})" for u in not_in_discord]
            )
            embed = discord.Embed(
                title="Discord Check",
                description=f"There are **{len(not_in_discord)}** players **NOT** in the discord!\n> {formatted}",
                color=discord.Color(0x1E77BE),
            )
        else:
            embed = all_players_in_discord_embed(guild)

        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f"Running {BOT_VERSION}")
        return embed

    except Exception as e:
        raise e

# ---------------------- /discord check ----------------------

@discord_group.command(name="check", description="Check which players are not in the Discord.")
async def discord_check(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        embed = await fetch_discord_check_embed(interaction.guild)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(get_erlc_error_message(0, exception=e))

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

        # Fetch kill logs
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
            kill_events = []
            for entry in data:
                ts = entry.get("Timestamp", 0)

                # Split "Username:UserId"
                killer_raw = entry.get("Killer", "Unknown:0")
                victim_raw = entry.get("Killed", "Unknown:0")

                if ":" in killer_raw:
                    killer_name, killer_id = killer_raw.split(":", 1)
                else:
                    killer_name, killer_id = killer_raw, "0"

                if ":" in victim_raw:
                    victim_name, victim_id = victim_raw.split(":", 1)
                else:
                    victim_name, victim_id = victim_raw, "0"

                # Build Roblox profile links if ID is valid
                killer_link = (
                    f"[{killer_name}](https://www.roblox.com/users/{killer_id}/profile)"
                    if killer_id != "0" else killer_name
                )
                victim_link = (
                    f"[{victim_name}](https://www.roblox.com/users/{victim_id}/profile)"
                    if victim_id != "0" else victim_name
                )

                kill_events.append(f"{killer_link} killed {victim_link} at <t:{ts}:F>")

            description = "\n".join(kill_events)

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

# ---------------------- prefix commands that have erlc at the start .erlc info, .erlc players, .erlc code, .erlc kills, .erlc command ----------------------

@bot.command(name="erlc")
async def erlc(ctx, subcommand: str = None):
    """Prefix command: .erlc <subcommand>"""
    if not subcommand:
        return await ctx.send("❌ Unknown command. Please use the `/erlc` slash command.")

    subcommand = subcommand.lower()
    handlers = {
        "info": handle_erlc_info,
        "players": handle_erlc_players,
        "code": handle_erlc_code,
        "kills": handle_erlc_kills,
        "command": handle_erlc_command,
    }

    handler = handlers.get(subcommand)
    if handler:
        await handler(ctx)
    else:
        await ctx.send(f"❌ Unknown subcommand `{subcommand}`. Please use the `/erlc` slash command.")


# --- Helper Functions ---

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

# ---------------------- commmand info ----------------------
command_categories = {
    "🛠️ General": [
        ("ping", "Check if the bot is online"),
        ("uptime", "Check the bots uptime"),
        ("Sync", "Sync slash commands owner only + prefix only"),
        ("servers", "owner only see all servers that the bots in"),
        ("help", "show info about a command"),
        ("commands", "show all commands")
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
        ("erlc code", "Show the erlc code")
    ],
    "🔒 Channel Management": [
        ("N/A", "N/A")
    ],
    "💼 Other": [
        ("N/A", "N/A")
    ]
}

# ---------------------- .commands ----------------------

@bot.command(name="commands", description="Show all available commands")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="Bot Commands List",
        description=f"Explore the available commands grouped by category. Use `{COMMAND_PREFIX}help [command name]` or `/help [command name]` for more details.",
        color=discord.Color(0x1E77BE)
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
        color=discord.Color(0x1E77BE)
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
        "useage": f"`{COMMAND_PREFIX}sync"
    }
    # Add all other commands here in the same structure
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
            color=discord.Color(0x1E77BE)
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