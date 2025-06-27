import os
from flask import Flask, render_template_string, jsonify
import aiohttp
import asyncio
import nest_asyncio
from threading import Thread

nest_asyncio.apply()

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("ERROR: PRC_API_KEY environment variable not set!")
    HEADERS = {}
else:
    HEADERS = {"server-key": API_KEY, "Accept": "application/json"}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SWAT Roleplay Community - ER:LC Server Info</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    body {
        background: #1f1f2e;
        color: #eee;
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 0;
    }
    .container {
        max-width: 900px;
        margin: 40px auto;
        padding: 25px;
        background: #2c2c44;
        border-radius: 15px;
        box-shadow: 0 0 25px #F39C12AA;
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
        box-shadow: 0 0 15px #F39C12AA;
        border: 3px solid #F39C12;
        object-fit: cover;
    }
    h1 {
        text-align: center;
        margin-bottom: 30px;
        font-weight: 700;
        color: #F39C12;
        text-shadow: 0 0 5px #F39C12;
    }
    .stats {
        display: flex;
        justify-content: space-around;
        margin-bottom: 30px;
        flex-wrap: wrap;
        gap: 15px;
    }
    .stat-card {
        background: #3a3a5c;
        padding: 15px 25px;
        border-radius: 12px;
        text-align: center;
        flex: 1 1 120px;
        box-shadow: 0 0 15px #F39C12AA;
        transition: background 0.3s ease;
    }
    .stat-card:hover {
        background: #4a4a7c;
    }
    .stat-card h2 {
        margin: 0 0 10px 0;
        font-size: 22px;
        color: #f5b041;
    }
    .stat-card p {
        font-size: 18px;
        margin: 0;
    }
    .players-section {
        background: #3a3a5c;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 0 15px #F39C12AA;
        max-height: 350px;
        overflow-y: auto;
    }
    .players-section h2 {
        margin-top: 0;
        margin-bottom: 15px;
        color: #f5b041;
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
        border-bottom: 1px solid #4a4a7c;
        font-weight: 500;
        font-size: 16px;
        color: #ddd;
    }
    ul.player-list li:last-child {
        border-bottom: none;
    }
    footer {
        text-align: center;
        padding: 15px 0;
        color: #999;
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

fetchData();
setInterval(fetchData, 10000);
</script>
</body>
</html>
"""

async def fetch_api(session, url):
    try:
        async with session.get(url, headers=HEADERS) as resp:
            print(f"Request to {url} returned status {resp.status}")
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                print(f"Error response body: {text}")
                return None
    except Exception as e:
        print(f"Exception during fetch_api({url}): {e}")
        return None


@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/data")
def get_data():
    return jsonify(asyncio.run(fetch_data()))

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        server_info = await fetch_api(session, "https://api.policeroleplay.community/v1/server")
        if not server_info:
            return {
                "players_count": "N/A",
                "queue_count": "N/A",
                "staff_in_game_count": "N/A",
                "owner_in_game": False,
                "players": []
            }

        players_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/players") or []
        queue_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/queue") or []
        staff_data = await fetch_api(session, "https://api.policeroleplay.community/v1/server/staff") or {}

        admins = staff_data.get("Admins", {})
        mods = staff_data.get("Mods", {})
        coowners = staff_data.get("CoOwners", [])

        staff_ids = set()
        for k in admins.keys():
            try:
                staff_ids.add(int(k))
            except:
                pass
        for k in mods.keys():
            try:
                staff_ids.add(int(k))
            except:
                pass
        for co in coowners:
            try:
                staff_ids.add(int(co))
            except:
                pass

        staff_in_game_count = 0
        owner_in_game = False
        players_list = []

        for player in players_data:
            pname_id = player.get("Player", "")
            if ":" not in pname_id:
                continue
            pname, pid = pname_id.split(":")
            try:
                pid_int = int(pid)
            except:
                continue

            players_list.append(pname)

            if pid_int in staff_ids:
                staff_in_game_count += 1
            if pid_int == server_info.get("OwnerId"):
                owner_in_game = True

        return {
            "players_count": len(players_data),
            "queue_count": len(queue_data),
            "staff_in_game_count": staff_in_game_count,
            "owner_in_game": owner_in_game,
            "players": players_list
        }

def keep_alive():
    def run():
        app.run(host="0.0.0.0", port=8080)
    thread = Thread(target=run)
    thread.start()
