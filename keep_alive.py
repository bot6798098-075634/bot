from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SWAT Roleplay Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #0d1b2a;
                color: #e0e1dd;
                text-align: center;
                padding-top: 100px;
            }
            h1 {
                color: #3a86ff;
                text-shadow: 0 0 8px #3a86ff;
            }
            p {
                font-size: 18px;
            }
        </style>
    </head>
    <body>
        <h1>🤖 SWAT Roleplay Discord Bot</h1>
        <p>Status: <strong>Online</strong></p>
        <p>This bot powers ER:LC sessions, moderation, and more.</p>
    </body>
    </html>
    """

def keep_alive():
    def run():
        app.run(host="0.0.0.0", port=8080)
    thread = Thread(target=run)
    thread.start()
