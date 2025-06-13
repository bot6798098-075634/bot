from discord.ext import commands

class ERLCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    API_KEY = os.getenv("API_KEY")

API_BASE = "https://api.policeroleplay.community/v1/server"
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
def get_error_message(http_status: int, api_code: int | None = None) -> str:
    if http_status == 400:
        return "❌ **400 – Bad Request**: Check your data formatting."
    if http_status == 403:
        return "❌ **403 – Unauthorized**: Invalid or missing server key."
    if http_status == 422:
        return "⚠️ **422 – No Players**: Server has no players online."
    if http_status == 500:
        return "💥 **500 – Server Error**: PRC or Roblox issue. Try again."

    if api_code is None:
        return f"❌ **Unexpected Error** – HTTP Status `{http_status}`"

    prc_errors = {
        0: "❌ **0 – Unknown Error**: Contact PRC support if persistent.",
        1001: "🔁 **1001 – Roblox Communication Error**: In-game server problem.",
        1002: "💥 **1002 – Internal System Error**: PRC system issue.",
        2000: "🔑 **2000 – Missing server-key**: Provide your key in headers.",
        2001: "🔑 **2001 – Malformed server-key**: Check format.",
        2002: "🔑 **2002 – Invalid/Expired server-key**.",
        2003: "🔐 **2003 – Invalid global API key**.",
        2004: "🚫 **2004 – Banned server-key**: Contact PRC.",
        3001: "⚙️ **3001 – Invalid Command**: Check your `:command` syntax.",
        3002: "🛑 **3002 – Server Offline**: No players are online.",
        4001: "🐌 **4001 – Rate Limited**: Slow down.",
        4002: "🚷 **4002 – Restricted Command**: Not allowed via API.",
        4003: "🧼 **4003 – Prohibited Message**: Message is blocked.",
        9998: "🔒 **9998 – Resource Restricted**.",
        9999: "📤 **9999 – Outdated Server Module**: Kick all players and restart.",
    }

    return prc_errors.get(api_code, f"❓ **Unknown PRC Error** `{api_code}` (HTTP {http_status})")

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
        # Extract the message after ":log "
        message_to_log = command[5:].strip()
        if not message_to_log:
            await interaction.followup.send("❌ You must provide a message after ':log'.")
            return

        # Construct the command to send to the API
        # Assuming the game command to send a chat message is ':say <message>'
        in_game_command = f":say [LOG] {message_to_log}"

        # Log embed for the log message command
        embed = discord.Embed(
            title="🛠 In-Game Log Message Sent",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
        embed.add_field(name="Message", value=message_to_log, inline=False)
        embed.set_footer(text="PRC Command Log")
        await send_embed(COMMAND_LOG_CHANNEL_ID, embed)

        # Send command to API
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
                await interaction.followup.send(f"⚠️ Exception occurred: `{e}`")
                return

        await interaction.followup.send(f"✅ Log message sent in-game: `{message_to_log}`")
        return

    # Regular command flow for all other commands

    # Log embed
    embed = discord.Embed(
        title="🛠 Command Executed",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
    embed.add_field(name="Command", value=f"`{command}`", inline=False)
    embed.set_footer(text="PRC Command Log")
    await send_embed(COMMAND_LOG_CHANNEL_ID, embed)

    # API call
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
            await interaction.followup.send(f"⚠️ Exception occurred: `{e}`")
            return

    await interaction.followup.send(f"✅ Command `{command}` sent successfully.")


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

@bot.tree.command(name="erlc_killlog", description="Fetch the latest kill logs")
async def kill_log(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/killlogs", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch kill logs, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No kill logs found.")
        return

    embed = discord.Embed(
        title="🔪 Kill Logs",
        color=discord.Color.red(),
        timestamp = datetime.now(timezone.utc)
    )
    for entry in data:
        ts = entry.get("Timestamp", 0)
        killer = entry.get("Killer", "Unknown")
        killed = entry.get("Killed", "Unknown")
        embed.add_field(name=f"Killed at {datetime.datetime.fromtimestamp(ts, UTC)}", value=f"{killer} killed {killed}", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="erlc_info", description="Get SWAT Roleplay Community server info")
async def erlc_info(interaction: discord.Interaction):
    await interaction.response.defer()  # In case it takes some time

    headers = {
        "server-key": API_KEY,
        "Accept": "*/*"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(API_BASE, headers=headers) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch server info (status {resp.status})")
                return

            data = await resp.json()

    # Extract data
    server_name = data.get("Name", "Unknown")
    join_code = data.get("JoinKey", "N/A")
    current_players = data.get("CurrentPlayers", 0)
    max_players = data.get("MaxPlayers", 0)

    # Fetch queue count from /server/queue
    queue_url = "https://api.policeroleplay.community/v1/server/queue"
    async with aiohttp.ClientSession() as session:
        async with session.get(queue_url, headers=headers) as resp:
            if resp.status == 200:
                queue_data = await resp.json()
                queue_count = len(queue_data)
            else:
                queue_count = 0

    embed = discord.Embed(title="SWAT Roleplay Community", color=0x1F8B4C)
    embed.add_field(name="Server Name", value=server_name, inline=False)
    embed.add_field(name="Join Code", value=join_code, inline=False)
    embed.add_field(name="Players", value=f"Current Players: {current_players}/{max_players}", inline=False)
    embed.add_field(name="Queue", value=f"{queue_count} players", inline=False)
    embed.set_footer(text="Powered by PRC API")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="erlc_bans", description="Get the list of banned players")
async def erlc_bans(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/bans", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch banned players, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No banned players found.")
        return

    embed = discord.Embed(
        title="🚫 Banned Players",
        color=discord.Color.red(),
        timestamp = datetime.now(timezone.utc)
    )
    for ban in data:
        player = ban.get("Player", "Unknown")
        reason = ban.get("Reason", "No reason provided")
        embed.add_field(name=player, value=reason, inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="erlc_players", description="Get the list of online players")
async def erlc_players(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/players", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch online players, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No online players found.")
        return

    embed = discord.Embed(
        title="👥 Online Players",
        color=discord.Color.green(),
        timestamp = datetime.now(timezone.utc)
    )
    for player in data:
        embed.add_field(name=player.get("Name", "Unknown"), value=f"ID: {player.get('ID', 'Unknown')}", inline=False)

    await interaction.followup.send(embed=embed)

def send_erlc_vehicles_command():
    url = f"{API_BASE}/command"
    headers = {
        "server-key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "command": "/erlc_vehicles"
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        print("Command sent successfully!")
        print("Response:", response.json())
    else:
        print(f"Failed to send command: {response.status_code}")
        print("Response:", response.text)

send_erlc_vehicles_command()

@bot.tree.command(name="erlc_modcalls", description="Get the list of mod calls in the server")
async def erlc_modcalls(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/modcalls", headers=HEADERS_GET) as resp:
            if resp.status != 200:
                await interaction.followup.send(f"Failed to fetch mod calls, status: {resp.status}")
                return
            data = await resp.json()

    if not data:
        await interaction.followup.send("No mod calls found.")
        return

    embed = discord.Embed(
        title="📞 Mod Calls",
        color=discord.Color.purple(),
        timestamp = datetime.now(timezone.utc)
    )
    for call in data:
        embed.add_field(name=call.get("Caller", "Unknown"), value=f"Reason: {call.get('Reason', 'No reason provided')}", inline=False)

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





@bot.tree.command(name="ssd1", description="Send a server shutdown message to the ER:LC server")
async def ssd1(interaction: discord.Interaction):
    await interaction.response.defer()

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
            await interaction.followup.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players in Server ⚠️",
                description="There are no players currently in the server to receive the SSD message.",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
            return
        else:
            embed = discord.Embed(
                title="Failed to Send SSD Message ❌",
                description=f"API responded with status code `{response.status_code}`.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending SSD Message ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return

    await asyncio.sleep(240)  # 4 minutes

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
            await interaction.followup.send(embed=embed)
        elif response.status_code == 422:
            embed = discord.Embed(
                title="No Players to Kick ⚠️",
                description="Kick all failed — no players were left in the server.",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Failed to Kick ❌",
                description=f"API responded with status code `{response.status_code}` when kicking.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="Error Sending Kick Command ❌",
            description=f"An exception occurred: `{e}`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

# --- CONFIGURATION ---
WELCOME_TEMPLATE = "Welcome to the server!"
KICK_REASON = "Username not allowed (starts with All or Others)"
PLAYERCOUNT_VC_ID = 1381697147895939233  # VC that will show player count
QUEUE_VC_ID = 1381697165562347671        # VC that will show queue size
PLAYERCOUNT_PREFIX = "「🎮」In Game:"
QUEUE_PREFIX = "「⏳」In Queue:"
DISCORD_CHANNEL_ID = 1381267054354632745  # your target channel ID
STAFF_ROLE_ID = 1375985192174354442  # the Discord role ID to exempt users
PRC_VEHICLES_URL = "https://api.policeroleplay.community/v1/server/vehicles"

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

        guild = bot.get_guild(YOUR_GUILD_ID)
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
        resp = requests.get(PRC_VEHICLES_URL, headers=headers)
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

async def setup(bot):
    await bot.add_cog(ERLCCog(bot))
