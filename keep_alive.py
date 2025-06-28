from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "SWAT Roleplay Bot is alive!"

def keep_alive():
    def run():
        app.run(host='0.0.0.0', port=8080)
    thread = Thread(target=run)
    thread.start()
