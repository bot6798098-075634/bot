import os
import asyncio
import aiohttp
from flask import Flask, render_template_string, jsonify
from threading import Thread

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
HEADERS = {"server-key": API_KEY, "Accept": "application/json"}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SWAT Roleplay Community - ER:LC Server Info</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    body {
        background: #0d1117;
        color: #e6f1ff;
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 0;
    }
    .container {
        max-width: 900px;
        margin: 40px auto;
        padding: 25px;
        background: #161b22;
        border-radius: 15px;
        box-shadow: 0 0 25px #3498db88;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 15px;
    }
    .logo-container img {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        box-shadow: 0 0 15px #3498db88;
        border: 3px solid #3498db;
        object-fit: cover;
    }
    h1 {
        text-align: center;
        margin-bottom: 30px;
        font-weight: 700;
        color: #3498db;
        text-shadow: 0 0 5px #3498db;
    }
    .stats {
        display: flex;
        justify-content: space-around;
        margin-bottom: 30px;
        flex-wrap: wrap;
        gap: 15px;
    }
    .stat-card {
        background: #1f2a38;
        padding: 15px 25px;
        border-radius: 12px;
        text-align: center;
        flex: 1 1 120px;
        box-shadow: 0 0 15px #2980b988;
        transition: background 0.3s ease;
    }
    .stat-card:hover {
        background: #223344;
    }
    .stat-card h2 {
        margin: 0 0 10px 0;
        font-size: 22px;
        color: #5dade2;
    }
    .stat-card p {
        font-size: 18px;
        margin: 0;
    }
    .players-section {
        background: #1f2a38;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 0 15px #2980b988;
        max-height: 350px;
        overflow-y: auto;
    }
    .players-section h2 {
        margin-top: 0;
        margin-bottom: 15px;
        color: #5dade2;
        text-align: center;
        font-weight: 700;
    }
    ul.player-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    ul.player-list li {
        padding: 8px 12px;
        border-bottom: 1px solid #34495e;
        font-weight: 500;
        font-size: 16px;
        color: #d6eaf8;
    }
    ul.player-list li:last-child {
        border-bottom: none;
    }
    footer {
        text-align: center;
        padding: 15px 0;
        color: #7f8c8d;
        font-size: 14px;
        margin-top: 40px;
        user-select: none;
    }
</style>
</head>
<body>
<div class="container">
    <div class="logo-container">
        <img src="https://images-ext-1.discordapp.net/external/PiBV5Gc1y0XGSrS_xKZZTDTsFSHbYj7JNmZ7_30paYA/%3Fsize%3D1024/https/cdn.discordapp.com/icons/1343179590247645205/84d0898fb6fc8d1b07811e7b179629b4.png?format=webp&quality=lossless&width=625&height=625" alt="SWAT Roleplay Logo" />
    </div>
    <h1>SWAT Roleplay Community</h1>
    <div class="stats">
        <div class="stat-card">
            <h2>Players In-Game</h2>
            <p id="players_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Queue Count</h2>
            <p id="queue_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Staff In-Game</h2>
            <p id="staff_count">Loading...</p>
        </div>
        <div class="stat-card">
            <h2>Owner In-Game</h2>
            <p id="owner_status">Loading...</p>
        </div>
    </div>
    <div class="players-section">
        <h2>Players List</h2>
        <ul class="player-list" id="players_list">
            <li>Loading...</li>
        </ul>
    </div>
</div>
<footer>SWAT Roleplay Community</footer>

<script>
async function fetchData() {
    try {
        const response = await fetch('/data');
        const data = await response.json();

        document.getElementById('players_count').textContent = data.players_count;
        document.getElementById('queue_count').textContent = data.queue_count;
        document.getElementById('staff_count').textContent = data.staff_in_game_count;
        document.getElementById('owner_status').textContent = data.owner_in_game ? "Yes" : "No";

        const playersList = document.getElementById('players_list');
        playersList.innerHTML = '';

        if (data.players.length === 0) {
            playersList.innerHTML = '<li>No players online</li>';
        } else {
            for (const p of data.players) {
                const li = document.createElement('li');
                li.textContent = p;
                playersList.appendChild(li);
            }
        }
    } catch (err) {
        console.error('Error fetching data:', err);
        document.getElementById('players_count').textContent = 'Error';
        document.getElementById('queue_count').textContent = 'Error';
        document.getElementById('staff_count').textContent = 'Error';
        document.getElementById('owner_status').textContent = 'Error';
        document.getElementById('players_list').innerHTML = '<li>Error loading players</li>';
    }
}

// Initial fetch
fetchData();

// Refresh every 10 seconds
setInterval(fetchData, 10000);
</script>
</body>
</html>"""


async def fetch_api(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status == 200:
            return await resp.json()
        return None

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/data")
def data():
    return asyncio.run(fetch_data())

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        server_info = await fetch_api(session, "https://api.policeroleplay.community/v1/server") or {}
        players_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/players") or []
        queue_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/queue") or []
        staff_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/staff") or {}

        players_count = len(players_data)
        queue_count = len(queue_data)

        staff_ids = set()
        for group in ("Admins", "Mods"):
            for k in staff_data.get(group, {}):
                try: staff_ids.add(int(k))
                except: continue
        staff_ids.update(map(int, staff_data.get("CoOwners", [])))

        staff_in_game_count = 0
        owner_in_game = False
        players_list = []

        for player in players_data:
            pname_id = player.get("Player", "")
            if ":" not in pname_id:
                continue
            pname, pid = pname_id.split(":")
            try: pid_int = int(pid)
            except: continue

            players_list.append(pname)
            if pid_int in staff_ids:
                staff_in_game_count += 1
            if pid_int == server_info.get("OwnerId"):
                owner_in_game = True

        return {
            "players_count": players_count,
            "queue_count": queue_count,
            "staff_in_game_count": staff_in_game_count,
            "owner_in_game": owner_in_game,
            "players": players_list
        }

def run():
    app.run(host="0.0.0.0", port=8080, debug=False)

def keep_alive():
    Thread(target=run, daemon=True).start()

# Optional: uncomment if you're running this file standalone
# if __name__ == "__main__":
#     run()
