import discord
import logging
import os
import asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pymongo import MongoClient

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")  # Add this to your .env file
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["srpc_bot"]  # This is your database name
users_collection = db["users"]  # This is your first collection


# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Define bot prefix and description
bot = commands.Bot(command_prefix=".", intents=intents, description="SWAT Roleplay Community Bot")


# Automatically load all cogs from the 'cogs' directory
def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print("-------------------------------------------------------------------------")

    # Start background task for presence updates
    update_presence.start()


@tasks.loop(count=1)
async def update_presence():+
    # First presence: watching over the server
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server"),
    )

    # Wait 5 minutes
    await asyncio.sleep(300)

    # Second presence: watching .help
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name=".help"),
    )


if __name__ == "__main__":
    load_cogs()
    if not TOKEN:
        logger.error("DISCORD_TOKEN is missing from environment variables.")
    else:
        bot.run(TOKEN)
