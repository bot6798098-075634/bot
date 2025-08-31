import discord
import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
cluster = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = cluster["srpc_bot"]  # <-- database name
collection = db["anti_nuke"]  # <-- collection for guild settings

async def get_guild_settings(guild_id):
    settings = await collection.find_one({"guild_id": guild_id})
    if not settings:
        # Insert default settings if not exist
        settings = {
            "guild_id": guild_id,
            "whitelisted_roles": [],
            "whitelisted_users": [],
            "whitelisted_channels": [],
            "anti_ban": True,
            "anti_kick": True,
            "anti_role_delete": True,
        }
        await collection.insert_one(settings)
    return settings

async def punish_executor(executor, reason="Anti-Nuke"):
    # Remove all roles except @everyone
    roles = [r for r in executor.roles if r != executor.guild.default_role]
    if roles:
        await executor.remove_roles(*roles, reason=reason)
