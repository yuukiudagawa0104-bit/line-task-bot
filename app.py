import os
import hashlib
import hmac
import base64
import json
import requests
import sqlite3
from datetime import datetime
from flask import Flask, request, abort

app = Flask(__name__)

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# =========================
# SQLite: user管理
# =========================
def get_or_create_user(user_id):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        mode TEXT,
        created_at TEXT
    )
    """)

    cur.execute(
        "SELECT mode FROM users WHERE user_id = ?",
        (user_id,)
    )
    user = cur.fetchone()

    if user is None:
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (user_id, "normal", datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return "normal"
    else:
        conn.close()
        return user[0]

def set_user_mode(user_id, mode):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET mode = ? WHERE user_id = ?",
        (mode, user_id)
    )
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        content TEXT,
        created_at TEXT,
        done INTEGER
    )
    """)

    conn.commit()
    conn.close()

def add_task(user_id, content):
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (user_id, content, created_at, done) VALUES (?, ?, ?, ?)",
        (user_id, content, datetime.now().isoformat(), 0)
    )
    conn.commit()
    conn.close()

# =========================
# 基本ルーティング
# =========================
@app.route("/", methods=["GET"])
def home():
    return "LINE Task Bot is running"

def verify_signature(body, signature):
    hash = hmac.new(
        CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    return base64.b64encode(hash).decode("utf-8") == signature

# =========================
# Webhook
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data()

    if not verify_signature(body, signature):
        abort(400)

    events = json.loads(body.decode("utf-8")).get("events", [])

    for event in events:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            reply_token = event["replyToken"]
            text = event["message"]["text"]

            # ★ ここが今回の本題
            mode = get_or_create_user(user_id)
            if text == "タスク追加":
                set_user_mode(user_id, "add_task")
                reply_message(reply_token, "タスク登録を開始します。内容を送ってください。")
                continue

            if text == "停止":
                set_user_mode(user_id, "pause")
                reply_message(reply_token, "リマインドを停止しました。")
                continue

            if mode == "add_task":
                add_task(user_id, text)
                set_user_mode(user_id, "normal")
                reply_message(reply_token, "タスクを登録しました。")
                continue


            reply_message(reply_token, f"[mode: {mode}]\n{text}")

    return "OK"

# =========================
# LINE返信
# =========================
def reply_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    requests.post(url, headers=headers, json=data)

# =========================
# 起動
# =========================
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
