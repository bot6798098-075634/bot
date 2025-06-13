import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # required for commands in discord.py 2.0+

bot = commands.Bot(command_prefix="!", intents=intents)

# Load cog when the bot starts
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    await bot.load_extension("cogs.example")  # load cog from cogs/example.py

bot.run("YOUR_BOT_TOKEN")
