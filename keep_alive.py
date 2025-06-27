import os
import time
import asyncio
import aiohttp
from flask import (
    Flask, render_template_string, request, redirect, url_for, session, abort, flash, make_response, jsonify
)
from requests_oauthlib import OAuth2Session

# Allow OAuth2 over HTTP for localhost development only
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # Change for production!

# Discord OAuth2 credentials - replace or use env vars
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1310388306764369940")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "aoE_MyuJf8Jec-pS8tiz0lqU6delYe4S")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")

# OAuth2 scopes
OAUTH2_SCOPE = ["identify", "guilds"]

# Allowed staff Discord user IDs (ints)
ALLOWED_STAFF_IDS = {1276264248095412387, 1338177398390132799, 1296842183344918570, 699197216933412896, 1276855258987106314, 1349385378766917643}

# API key for ER:LC API
API_KEY = os.getenv("API_KEY")
HEADERS = {"server-key": API_KEY, "Accept": "application/json"}

# In-memory announcements (replace with DB for production)
announcements_store = []

# In-memory current viewers tracking:
# key = user_id (str), value = dict { "name": username#discrim, "last_seen": timestamp }
current_viewers = {}
VIEWER_TIMEOUT = 60  # seconds

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SWAT Roleplay Community - ER:LC Server Info</title>
<link rel="icon" href="https://cdn.discordapp.com/icons/1343179590247645205/84d0898fb6fc8d1b07811e7b179629b4.png?size=64" type="image/png">

<style>
body { background: #121f3e; color: #d0e4ff; font-family: 'Roboto', sans-serif; margin:0; padding:0; }
.container { max-width:960px; margin:40px auto; padding:25px; background:#1b2a5e; border-radius:15px; box-shadow:0 0 25px #3b6eeaaa;}
.logo-container { display:flex; justify-content:center; margin-bottom:20px;}
.logo-container img { width:120px; height:120px; border-radius:50%; box-shadow:0 0 15px #3b6eeaaa; border:3px solid #3b6eea; object-fit:cover;}
h1 { text-align:center; margin-bottom:30px; font-weight:700; color:#3b6eea; text-shadow:0 0 8px #3b6eea;}
.stats { display:flex; justify-content:space-around; margin-bottom:30px; flex-wrap:wrap; gap:15px;}
.stat-card { background:#27408b; padding:15px 25px; border-radius:12px; text-align:center; flex:1 1 140px; box-shadow:0 0 15px #3b6eeaaa; transition: background 0.3s ease; color:#cde1ff;}
.stat-card:hover { background:#3b6eea; color:white;}
.stat-card h2 { margin:0 0 10px 0; font-size:22px; color:#a8c8ff;}
.stat-card p { font-size:18px; margin:0; font-weight:700;}
.section { background:#27408b; border-radius:12px; padding:20px; box-shadow:0 0 15px #3b6eeaaa; margin-bottom:30px; max-height:350px; overflow-y:auto;}
.section h2 { margin-top:0; margin-bottom:15px; color:#a8c8ff; text-align:center; font-weight:700; text-shadow:0 0 5px #3b6eea;}
ul.list { list-style:none; padding:0; margin:0; font-size:16px;}
ul.list li { padding:6px 10px; border-bottom:1px solid #3b6eea; font-weight:500; color:#d0e4ff;}
ul.list li:last-child { border-bottom:none;}
button.logout-btn { background:#bb3b3b; margin:10px auto 30px auto; display:block; width:80px; cursor:pointer; border:none; border-radius:5px; color:#fff; font-weight:700; }
button.logout-btn:hover { background:#992929; }
form#announcement_form { display:flex; gap:10px; justify-content:center; margin-top:10px;}
form#announcement_form input[type="text"] { flex:1; padding:8px; border-radius:5px; border:none; }
form#announcement_form button { padding:8px 15px; border:none; border-radius:5px; background:#3b6eea; color:white; font-weight:700; cursor:pointer;}
form#announcement_form button:hover { background:#2c53b8;}
.flash-message { text-align:center; color:#f55; margin-bottom:15px; font-weight:700;}
</style>
</head>
<body>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <div class="flash-message">
      {% for message in messages %}
        <p>{{ message }}</p>
      {% endfor %}
    </div>
  {% endif %}
{% endwith %}

{% if not session.get('discord_token') %}
<div style="max-width: 320px; margin: 150px auto; background: #27408b; padding: 25px; border-radius: 15px; box-shadow: 0 0 25px #3b6eeaaa; color:#d0e4ff; font-weight:700; text-align:center;">
    <h2>Staff Login with Discord</h2>
    <a href="{{ url_for('login') }}" style="display:inline-block; margin-top:20px; padding:12px 25px; background:#3b6eea; color:white; border-radius:8px; text-decoration:none; font-weight:700;">Login with Discord</a>
</div>
{% else %}
<div class="container" role="main">
    <button class="logout-btn" onclick="window.location.href='{{ url_for('logout') }}'">Logout</button>
    <div class="logo-container">
        <img src="https://cdn.discordapp.com/icons/1343179590247645205/84d0898fb6fc8d1b07811e7b179629b4.png?size=512" alt="SWAT Roleplay Logo" />
    </div>
    <h1>SWAT Roleplay Community</h1>
    <p style="text-align:center; font-weight:bold; margin-bottom:20px;">Logged in as: {{ session['discord_user']['username'] }}#{{ session['discord_user']['discriminator'] }}</p>
    
    <div class="stats" aria-label="Server Statistics">
        <div class="stat-card" tabindex="0">
            <h2>Players In-Game</h2>
            <p id="players_count">Loading...</p>
        </div>
        <div class="stat-card" tabindex="0">
            <h2>Queue Count</h2>
            <p id="queue_count">Loading...</p>
        </div>
        <div class="stat-card" tabindex="0">
            <h2>Staff In-Game</h2>
            <p id="staff_count">Loading...</p>
        </div>
        <div class="stat-card" tabindex="0">
            <h2>Owner In-Game</h2>
            <p id="owner_status">Loading...</p>
        </div>
        <div class="stat-card" tabindex="0">
            <h2>API Latency (ms)</h2>
            <p id="latency_ms">Loading...</p>
        </div>
    </div>

    <div class="section" aria-label="Currently Viewing">
        <h2>Currently Viewing</h2>
        <ul class="list" id="viewers_list">
            <li>Loading...</li>
        </ul>
    </div>

    <div class="section" aria-label="Announcements">
        <h2>Announcements / Alerts</h2>
        <ul class="list" id="announcements_list">
            <li>No announcements</li>
        </ul>
        <form id="announcement_form" method="POST" action="{{ url_for('add_announcement') }}" aria-label="Add Announcement">
            <input type="text" name="announcement" placeholder="Add new announcement..." required aria-required="true" />
            <button type="submit">Add</button>
        </form>
    </div>

    <div class="section" aria-label="Players List">
        <h2>Players List</h2>
        <ul class="list" id="players_list">
            <li>Loading...</li>
        </ul>
    </div>

    <div class="section" aria-label="Command Logs">
        <h2>Recent Command Logs</h2>
        <ul class="list" id="command_logs_list">
            <li>Loading...</li>
        </ul>
    </div>

    <div class="section" aria-label="Vehicles List">
        <h2>Vehicles</h2>
        <ul class="list" id="vehicles_list">
            <li>Loading...</li>
        </ul>
    </div>
</div>

<script>
async function sendHeartbeat() {
    try {
        await fetch('/heartbeat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
    } catch (e) {
        console.error('Heartbeat failed', e);
    }
}

async function updateViewers(viewers) {
    const viewersList = document.getElementById('viewers_list');
    viewersList.innerHTML = '';
    if (viewers.length === 0) {
        viewersList.innerHTML = '<li>No viewers online</li>';
    } else {
        viewers.forEach(v => {
            const li = document.createElement('li');
            li.textContent = v;
            viewersList.appendChild(li);
        });
    }
}

async function fetchData() {
    try {
        const response = await fetch('/data');
        const data = await response.json();

        document.getElementById('players_count').textContent = data.players_count;
        document.getElementById('queue_count').textContent = data.queue_count;
        document.getElementById('staff_count').textContent = data.staff_in_game_count;
        document.getElementById('owner_status').textContent = data.owner_in_game ? "Yes" : "No";
        document.getElementById('latency_ms').textContent = data.latency_ms;

        updateViewers(data.viewers);

        const announcementsList = document.getElementById('announcements_list');
        announcementsList.innerHTML = '';
        if (data.announcements.length === 0) {
            announcementsList.innerHTML = '<li>No announcements</li>';
        } else {
            data.announcements.forEach(a => {
                const li = document.createElement('li');
                li.textContent = a;
                announcementsList.appendChild(li);
            });
        }

        const playersList = document.getElementById('players_list');
        playersList.innerHTML = '';
        if (data.players.length === 0) {
            playersList.innerHTML = '<li>No players online</li>';
        } else {
            data.players.forEach(p => {
                const li = document.createElement('li');
                li.textContent = p;
                playersList.appendChild(li);
            });
        }

        const logsList = document.getElementById('command_logs_list');
        logsList.innerHTML = '';
        if (data.command_logs.length === 0) {
            logsList.innerHTML = '<li>No recent commands</li>';
        } else {
            data.command_logs.forEach(log => {
                const li = document.createElement('li');
                li.textContent = log;
                logsList.appendChild(li);
            });
        }

        const vehiclesList = document.getElementById('vehicles_list');
        vehiclesList.innerHTML = '';
        if (data.vehicles.length === 0) {
            vehiclesList.innerHTML = '<li>No vehicles data</li>';
        } else {
            data.vehicles.forEach(v => {
                const li = document.createElement('li');
                li.textContent = `${v.Name || "Unknown"} (${v.Type || "N/A"}) - $${v.Price || "N/A"}`;
                vehiclesList.appendChild(li);
            });
        }
    } catch (err) {
        console.error('Error fetching data:', err);
    }
}
fetchData();
setInterval(fetchData, 10000);
setInterval(sendHeartbeat, 30000);  // send heartbeat every 30 seconds
</script>
{% endif %}
</body>
</html>
"""

@app.errorhandler(403)
def unauthorized(e):
    return make_response(render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>403 Unauthorized - SWAT Roleplay Community</title>
    <style>
        body {
            background: #121f3e;
            color: #d0e4ff;
            font-family: 'Roboto', sans-serif;
            margin: 0; padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .error-container {
            background: #1b2a5e;
            border-radius: 15px;
            box-shadow: 0 0 25px #3b6eeaaa;
            padding: 40px 50px;
            text-align: center;
            max-width: 400px;
            width: 90%;
        }
        .error-container h1 {
            font-size: 72px;
            color: #bb3b3b;
            margin-bottom: 10px;
            text-shadow: 0 0 15px #bb3b3b;
        }
        .error-container h2 {
            color: #3b6eea;
            font-weight: 700;
            margin-bottom: 20px;
            text-shadow: 0 0 10px #3b6eea;
        }
        .error-container p {
            font-size: 18px;
            margin-bottom: 30px;
            color: #cde1ff;
        }
        .error-container a {
            display: inline-block;
            padding: 12px 25px;
            background: #3b6eea;
            color: white;
            border-radius: 8px;
            font-weight: 700;
            text-decoration: none;
            box-shadow: 0 0 10px #3b6eea;
            transition: background 0.3s ease;
        }
        .error-container a:hover {
            background: #2c53b8;
        }
    </style>
    </head>
    <body>
        <div class="error-container" role="main" aria-labelledby="error-title" aria-describedby="error-desc">
            <h1 id="error-title">403</h1>
            <h2>Unauthorized</h2>
            <p id="error-desc">Sorry, you do not have permission to access this page.<br/>Please login with an authorized Discord account.</p>
            <a href="{{ url_for('login') }}">Login with Discord</a>
        </div>
    </body>
    </html>
    """), 403)

def make_discord_oauth_session(state=None, token=None):
    return OAuth2Session(
        client_id=DISCORD_CLIENT_ID,
        redirect_uri=DISCORD_REDIRECT_URI,
        scope=OAUTH2_SCOPE,
        state=state,
        token=token,
    )

@app.route("/login")
def login():
    discord = make_discord_oauth_session()
    authorization_url, state = discord.authorization_url(
        "https://discord.com/api/oauth2/authorize",
        prompt="consent",
    )
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    if request.values.get("error"):
        return f"Error: {request.values['error']}", 400
    discord = make_discord_oauth_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        "https://discord.com/api/oauth2/token",
        client_secret=DISCORD_CLIENT_SECRET,
        authorization_response=request.url,
    )
    session['discord_token'] = token
    discord = make_discord_oauth_session(token=token)
    user = discord.get("https://discord.com/api/users/@me").json()

    if int(user["id"]) not in ALLOWED_STAFF_IDS:
        session.clear()
        abort(403, "Unauthorized user")

    session['discord_user'] = user
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

async def fetch_api(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status == 200:
            return await resp.json()
        return None

@app.route("/data")
def get_data():
    # Remove expired viewers first
    now = time.time()
    expired_keys = [k for k,v in current_viewers.items() if now - v["last_seen"] > VIEWER_TIMEOUT]
    for k in expired_keys:
        del current_viewers[k]
    return asyncio.run(fetch_data())

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        start_time = time.perf_counter()

        server_info = await fetch_api(session, "https://api.policeroleplay.community/v1/server")
        if not server_info:
            return {
                "players_count": "N/A",
                "queue_count": "N/A",
                "staff_in_game_count": "N/A",
                "owner_in_game": False,
                "players": [],
                "announcements": announcements_store,
                "command_logs": [],
                "vehicles": [],
                "latency_ms": -1,
                "viewers": [],
            }

        players_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/players") or []
        queue_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/queue") or []
        staff_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/staff") or {}
        cmd_logs_raw = await fetch_api(session, "https://api.policeroleplay.community/v1/server/commandlogs") or []
        vehicles = await fetch_api(session, "https://api.policeroleplay.community/v1/server/vehicles") or []

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        command_logs = []
        for log in cmd_logs_raw[:50]:
            timestamp = log.get("Timestamp", "Unknown")
            user = log.get("User", "Unknown")
            command = log.get("Command", "Unknown")
            command_logs.append(f"[{timestamp}] {user}: {command}")

        players_count = len(players_data)
        queue_count = len(queue_data)

        staff_ids = set()
        for key in ["Admins", "Mods", "CoOwners"]:
            group = staff_data.get(key)
            if isinstance(group, dict):
                for k in group.keys():
                    try:
                        staff_ids.add(int(k))
                    except:
                        pass
            elif isinstance(group, list):
                for x in group:
                    try:
                        staff_ids.add(int(x))
                    except:
                        pass

        staff_in_game_count = 0
        owner_in_game = False
        players_list = []

        for player in players_data:
            pname_id = player.get("Player", "")
            if ":" not in pname_id:
                continue
            pname, pid = pname_id.split(":", 1)
            try:
                pid_int = int(pid)
            except:
                pid_int = None
            players_list.append(pname)
            if pid_int in staff_ids:
                staff_in_game_count += 1
            if pid_int == server_info.get("OwnerId"):
                owner_in_game = True

        # Format viewers for output (usernames)
        viewers_list = [v["name"] for v in current_viewers.values()]

        return {
            "players_count": players_count,
            "queue_count": queue_count,
            "staff_in_game_count": staff_in_game_count,
            "owner_in_game": owner_in_game,
            "players": players_list,
            "announcements": announcements_store,
            "command_logs": command_logs,
            "vehicles": vehicles,
            "latency_ms": latency_ms,
            "viewers": viewers_list,
        }

@app.route("/add_announcement", methods=["POST"])
def add_announcement():
    if not session.get("discord_token"):
        abort(403)
    announcement = request.form.get("announcement", "").strip()
    if announcement:
        announcements_store.append(announcement)
        flash("Announcement added!")
    return redirect(url_for("index"))

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    if not session.get("discord_token") or "discord_user" not in session:
        # No user logged in - no heartbeat tracking
        return jsonify({"status": "unauthorized"}), 403
    user = session["discord_user"]
    user_id = str(user["id"])
    username = f'{user["username"]}#{user["discriminator"]}'
    current_viewers[user_id] = {"name": username, "last_seen": time.time()}
    return jsonify({"status": "ok"})

# if __name__ == "__main__":
  #  app.run(debug=True, port=5000)
