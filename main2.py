import discord
import asyncio
import aiohttp
import os
from datetime import datetime, timezone
from discord.ext import commands

# Create bot with intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# ========== Emojis ==========
bot.time_emoji = "<:time:1387841153491271770>"
bot.tick_emoji = "<:tick:1383796116763709532>"
bot.error_emoji = "<:error:1383587321294884975>"
bot.ping_emoji = "<:ping:1381073968873607229>"
bot.logo_emoji = "<:logo:1322987575375429662>"
bot.pong_emoji = "<:pong:1387845465315348480>"
bot.failed_emoji = "<:failed:1387853598733369435>"
bot.note_emoji = "<note:1387865341773873302>"
bot.clipboard_emoji = "<:clipboard:1387890654868410408>"
bot.owner_emoji = "<:owner:1387900933006164160>"

# ========== Role IDs ==========
bot.staff_role_id = 1343234687505530902
bot.mod_role_id = 1346576470360850432
bot.admin_role_id = 1346577013774880892
bot.superviser_role_id = 1346577369091145728
bot.management_role_id = 1346578020747575368
bot.ia_role_id = 1371537163522543647
bot.ownership_role_id = 1346578250381656124
bot.session_manager_role_id = 1374839922976100472
bot.staff_trainer_role_id = 1377794070440837160
bot.afk_role_id = 1355829296085729454
bot.event_role_id = 1346740470272757760
bot.staff_help_role_id = 1370096425282830437

# Global aiohttp session
session: aiohttp.ClientSession | None = None

# ========== On Ready ==========
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        await bot.tree.sync(guild=discord.Object(id=1343179590247645205))  # Optional guild sync
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    bot.start_time = datetime.now(timezone.utc)

    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()

    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name="over the server")
    )

    print(f"{bot.user} has connected to Discord and is watching over the server.")
    print("-----------------------------------------------------------------------")

# ========== Load Cogs ==========
initial_extensions = [
    "Cogs.uptime",
    "Cogs.ping",
    "Cogs.slowmode",
    "Cogs.afk",
]

async def load_cogs():
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded {extension}")
        except Exception as e:
            print(f"Failed to load {extension}: {e}")

# ========== Main Entrypoint ==========
if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()

    # Load cogs and run bot
    asyncio.run(load_cogs())
    bot.run(os.getenv("DISCORD_TOKEN"))
