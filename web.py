# web.py
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Discord bot is running!"

def keep_alive():
    import threading
    def run():
        app.run(host="0.0.0.0", port=10000)
    threading.Thread(target=run, daemon=True).start()
