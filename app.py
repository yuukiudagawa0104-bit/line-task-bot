from flask import Flask, request, abort

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "LINE Task Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    # 今は何もしない（後で実装）
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
