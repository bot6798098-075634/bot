# cogs/erlc.py
import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
import requests
import asyncio

# --- Constants you need to define or import ---
GUILD_ID = 123456789012345678  # your guild ID here
API_KEY = "YOUR_SERVER_KEY"
API_BASE = "https://api.policeroleplay.community/v1/server"
PLAYERCOUNT_VC_ID = 111111111111111111  # your VC channel IDs here
QUEUE_VC_ID = 222222222222222222
PLAYERCOUNT_PREFIX = "Players:"
QUEUE_PREFIX = "Queue:"
DISCORD_CHANNEL_ID = 333333333333333333  # channel to send staff livery alerts
STAFF_ROLE_ID = 444444444444444444

# Abbreviation dict for voice channels (example)
VC_ABBREVIATIONS = {
    "HQ": 555555555555555555,
    "PATROL": 666666666666666666,
    # etc...
}

# Roblox to Discord ID mapping example
ROBLOX_TO_DISCORD = {
    "RobloxUser1": 777777777777777777,
    # ...
}

# Restricted vehicles with allowed role IDs
RESTRICTED_VEHICLES = {
    "SomeVehicleName": [123456789012345678],  # role IDs allowed
}

# Roblox to Discord links (example)
ROBLOX_DISCORD_LINKS = {
    "RobloxUser1": 777777777777777777,
}

# Track welcomed and handled players
welcomed_players = set()
handled_usernames = set()

# Placeholder functions - you need to implement these
def get_join_logs():
    # Return list of join log dicts with keys "Join" and "Player"
    return []

def kick_user(player_name: str) -> bool:
    # Kick user logic
    return True

def send_welcome(player_name: str) -> bool:
    # Send welcome message logic
    return True

def fetch_command_logs():
    # Return command logs as list of dicts with keys "Command" and "Player"
    return []


class ERLCCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcomed_players = set()
        self.handled_usernames = set()
        self.notified_staff_vehicles = set()
        self.process_joins_loop.start()
        self.check_log_commands.start()
        self.update_vc_status.start()
        self.check_staff_livery.start()
        # Vehicle restrictions not started here, call separately if needed

    def cog_unload(self):
        self.process_joins_loop.cancel()
        self.check_log_commands.cancel()
        self.update_vc_status.cancel()
        self.check_staff_livery.cancel()

    @tasks.loop(seconds=60)
    async def process_joins_loop(self):
        logs = get_join_logs()
        for log in logs:
            if not log.get("Join"):
                continue
            player_raw = log.get("Player", "")
            player_name = player_raw.split(":")[0]

            if player_name in self.handled_usernames:
                continue

            if player_name.lower().startswith("all") or player_name.lower().startswith("others"):
                if kick_user(player_name):
                    print(f"⛔ Kicked {player_name} for restricted username.")
                else:
                    print(f"⚠️ Failed to kick {player_name}.")
            else:
                if player_name not in self.welcomed_players:
                    if send_welcome(player_name):
                        print(f"✅ Welcomed {player_name}")
                        self.welcomed_players.add(player_name)
                    else:
                        print(f"❌ Failed to welcome {player_name}")

            self.handled_usernames.add(player_name)

    @tasks.loop(seconds=100)
    async def check_log_commands(self):
        logs = fetch_command_logs()
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            print("❌ Guild not found")
            return

        for log in logs:
            command = log.get("Command", "")
            roblox_username = log.get("Player", "").split(":")[0]

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
    async def update_vc_status(self):
        guild = self.bot.get_guild(GUILD_ID)
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

    @tasks.loop(seconds=30)
    async def check_staff_livery(self):
        headers = {"server-key": API_KEY}
        try:
            resp = requests.get(f"{API_BASE}/vehicles", headers=headers)
            if resp.status_code != 200:
                print(f"Failed to fetch vehicles: {resp.status_code}")
                return

            vehicles = resp.json()

            # Filter vehicles with "STAFF TEAM" or "STAFF TEAM 2" in Texture or Name
            staff_vehicles = [v for v in vehicles if v.get("Texture", "").upper() in ("STAFF TEAM", "STAFF TEAM 2") or v.get("Name", "").upper() in ("STAFF TEAM", "STAFF TEAM 2")]

            channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
            if not channel:
                print("Channel not found")
                return

            for vehicle in staff_vehicles:
                owner_name = vehicle.get("Owner")
                if not owner_name:
                    continue

                guild = channel.guild
                member = discord.utils.find(lambda m: m.name == owner_name, guild.members)
                if not member:
                    continue

                if any(role.id == STAFF_ROLE_ID for role in member.roles):
                    continue

                # Prevent spamming: only notify once per owner + vehicle combination (optional)
                vehicle_id = vehicle.get("ID", f"{owner_name}-{vehicle.get('Name','unknown')}")
                if vehicle_id in self.notified_staff_vehicles:
                    continue
                self.notified_staff_vehicles.add(vehicle_id)

                embed = discord.Embed(
                    title="Staff Livery Detected",
                    description=f"User **{owner_name}** is using a staff vehicle livery!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Vehicle Name", value=vehicle.get("Name", "Unknown"), inline=True)
                embed.add_field(name="Texture", value=vehicle.get("Texture", "Unknown"), inline=True)
                embed.set_footer(text="PRC Server Monitor")

                await channel.send(embed=embed)

        except Exception as e:
            print(f"Error fetching or processing vehicles: {e}")

    # Slash command to set restriction
    @app_commands.command(name="set_restriction")
    @app_commands.describe(vehicle="Vehicle name", role="Role required")
    async def set_restriction(self, interaction: discord.Interaction, vehicle: str, role: discord.Role):
        RESTRICTED_VEHICLES[vehicle] = [role.id]
        await interaction.response.send_message(f"✅ Set restriction: `{vehicle}` → `{role.name}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ERLCCog(bot))
