from flask import Flask, render_template_string
from threading import Thread

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SWAT Roleplay Discord Bot</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      background-color: #0b132b;
      color: #f0f0f0;
      font-family: Arial, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
    }
    .container {
      text-align: center;
      max-width: 600px;
      background: #1c2541;
      padding: 30px;
      border-radius: 15px;
      box-shadow: 0 0 15px #3a506b;
    }
    h1 {
      color: #5bc0be;
    }
    p {
      font-size: 1.1em;
    }
    .status {
      margin-top: 20px;
      color: #6fffe9;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>SWAT Roleplay Discord Bot</h1>
    <p>This bot is currently online and being hosted using <strong>Render</strong>.</p>
    <div class="status">Status: ✅ Online</div>
    <p><small>URL: <code>https://bot-ej2s.onrender.com/</code></small></p>
  </div>
</body>
</html>
"""

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string(HTML)

# def keep_alive():
#    def run():
 #      app.run(host='0.0.0.0', port=8080)
#    t = Thread(target=run)
#    t.start()
