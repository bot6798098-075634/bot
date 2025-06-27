from flask import Flask, render_template_string, request
from threading import Thread
import datetime
import logging
import traceback

# === Logging Setup ===
logger = logging.getLogger("KeepAlive")
logger.setLevel(logging.INFO)

# Log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# Log to file
file_handler = logging.FileHandler("keep_alive.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# === Flask App ===
app = Flask(__name__)

# === HTML Status Page ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bot Status</title>
    <style>
        body {
            font-family: Consolas, monospace;
            background-color: #0e0e0e;
            color: #00ff00;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        p {
            font-size: 1.25rem;
            color: #ccc;
        }
        .small {
            font-size: 0.9rem;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>✅ Bot is Running</h1>
    <p>Last checked: {{ timestamp }}</p>
    <p class="small">IP: {{ ip }}</p>
</body>
</html>
"""

# === Routes ===

@app.route("/")
def home():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"Ping received from {ip}")
    return render_template_string(HTML_TEMPLATE, timestamp=now, ip=ip)

@app.errorhandler(404)
def not_found(e):
    logger.warning(f"404 Not Found: {request.path}")
    return "404 - Not Found", 404

@app.errorhandler(500)
def internal_error(e):
    logger.error("500 Internal Server Error:\n" + traceback.format_exc())
    return "500 - Internal Server Error", 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.error("Unhandled Exception:\n" + traceback.format_exc())
    return "An error occurred.", 500

# === Run Thread ===

def run():
    try:
        logger.info("Keep-alive Flask server is starting on port 8080...")
        app.run(host="0.0.0.0", port=8080)
    except Exception as e:
        logger.critical("Critical error in Flask server:\n" + traceback.format_exc())

def keep_alive():
    thread = Thread(target=run)
    thread.daemon = True
    thread.start()
    logger.info("Keep-alive background thread launched.")
