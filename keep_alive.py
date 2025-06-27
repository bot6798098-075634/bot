from flask import Flask

app = Flask("")

@app.route("/")
def home():
    return "Server is alive!"

def keep_alive():
    app.run(host="0.0.0.0", port=8080)
