from flask import Flask, render_template
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")  # Serve the HTML page

def run_web():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web, daemon=True).start()
