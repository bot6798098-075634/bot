from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web, daemon=True).start()
