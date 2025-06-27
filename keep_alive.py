import os
import asyncio
import aiohttp
from flask import Flask, render_template_string, jsonify
from threading import Thread

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
HEADERS = {"server-key": API_KEY, "Accept": "application/json"}

# Your full styled HTML
HTML = """<html lang="en"><head>...your full HTML from above...</head></html>"""

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
