import os
import json
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timezone
from web import keep_alive  # Single function now handles web + keep alive

# ───────────── Start Web Keep-Alive ─────────────
keep_alive()

# ───────────── Bot Configuration ─────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0)) if os.getenv("GUILD_ID") else None

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# ───────────── Logging ─────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ───────────── Warnings Save/Load ─────────────
def load_warnings():
    try:
        with open("warnings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warnings(data):
    with open("warnings.json", "w") as f:
        json.dump(data, f, indent=4)

warnings = load_warnings()

# ───────────── Event: Bot Ready ─────────────
@bot.event
async def on_ready():
    bot.start_time = datetime.now(timezone.utc)

    try:
        if GUILD_ID:
            await tree.sync(guild=discord.Object(id=GUILD_ID))
            logger.info(f"✅ Synced slash commands to guild {GUILD_ID}")
        else:
            await tree.sync()
            logger.info("✅ Synced slash commands globally")
    except Exception as e:
        logger.warning(f"⚠️ Failed to sync slash commands: {e}")

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    logger.info(f"✅ {bot.user} is online and watching the server.")
    logger.info("─────────────────────────────────────────────")

# ───────────── Load All Cogs ─────────────
for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and not filename.startswith("__"):
        try:
            bot.load_extension(f"cogs.{filename[:-3]}")
            logger.info(f"✅ Loaded cog: {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to load cog {filename}: {e}")

# ───────────── Run the Bot ─────────────
if TOKEN:
    bot.run(TOKEN)
else:
    logger.error("❌ DISCORD_TOKEN not set in .env")
