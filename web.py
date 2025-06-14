from flask import Flask, render_template, jsonify
import datetime

app = Flask(__name__)

# Simulated bot status data
bot_status = {
    "online": True,
    "start_time": datetime.datetime.utcnow()
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    uptime = datetime.datetime.utcnow() - bot_status["start_time"]
    status = {
        "online": bot_status["online"],
        "uptime": str(uptime).split('.')[0],  # Format: HH:MM:SS
        "start_time": bot_status["start_time"].strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    return jsonify(status)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
