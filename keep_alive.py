from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def keep_alive():
    def run():
        app.run(host="127.0.0.1", port=8080)
    thread = Thread(target=run)
    thread.start()
