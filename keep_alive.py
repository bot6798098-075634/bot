from flask import Flask, render_template_string
from threading import Thread

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SWAT Roleplay Bot Status</title>
  <style>
    body {
      background: #121f3e;
      color: #d0e4ff;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 0;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }
    .card {
      background: #1b2a5e;
      padding: 40px;
      border-radius: 15px;
      box-shadow: 0 0 25px #3b6eeaaa;
      text-align: center;
      max-width: 500px;
    }
    h1 {
      color: #3b6eea;
      margin-bottom: 20px;
      text-shadow: 0 0 8px #3b6eea;
    }
    p {
      font-size: 18px;
      line-height: 1.5;
    }
    a {
      color: #72aaff;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>🤖 SWAT Roleplay Discord Bot</h1>
    <p>Status: <strong>Online</strong></p>
    <p>This bot powers moderation, ER:LC integration, session management, and more for SWAT RP.</p>
    <p><a href="https://discord.gg/your-server">Join the Discord</a></p>
  </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

def keep_alive():
    def run():
        app.run(host="0.0.0.0", port=8080)
    thread = Thread(target=run)
    thread.start()
