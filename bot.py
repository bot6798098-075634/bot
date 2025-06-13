import os
import json
import logging
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timezone
from collections import defaultdict, deque
from keep_alive import keep_alive  # Flask keepalive
from threading import Thread
from web import app  # Optional: your Flask app

# ──────────── Flask Web Server ────────────
def run_web():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run_web).start()
keep_alive()

# ──────────── Bot Configuration ────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))  # Optional: for slash command sync

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# ──────────── Logging ────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ──────────── Warnings Save/Load ────────────
def load_warnings():
    try:
        with open('warnings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warnings(data):
    with open('warnings.json', 'w') as f:
        json.dump(data, f, indent=4)

warnings = load_warnings()

# ──────────── Event: Bot Ready ────────────
@bot.event
async def on_ready():
    bot.start_time = datetime.now(timezone.utc)

    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Synced slash commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}")

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    print(f"✅ {bot.user} is online and watching the server.")
    print("─────────────────────────────────────────────")

# ──────────── Load All Cogs ────────────
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")

# ──────────── Run the Bot ────────────
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not set in .env")
