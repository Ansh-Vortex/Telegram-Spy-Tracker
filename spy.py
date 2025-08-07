from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime, timedelta
import json, os
import pytz
from dotenv import load_dotenv
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- LOAD CONFIG ---
load_dotenv()

API_HASH = os.getenv("API_HASH")
API_ID = os.getenv("API_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = os.getenv("DATA_FILE", "users.json")
LOG_FOLDER = os.getenv("LOG_FOLDER", "logs")
IST = pytz.timezone("Asia/Kolkata")

# --- STORAGE INIT ---
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

def load_users():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# --- COMMAND HANDLERS ---

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 I'm tracking users! Use /add, /remove, /list, /info, /export.")

def add(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        return update.message.reply_text("Usage: /add userID name")

    user_id, name = context.args
    users = load_users()
    users[user_id] = name
    save_users(users)
    update.message.reply_text(f"✅ Added user: {name} (ID: {user_id})")

def remove(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        return update.message.reply_text("Usage: /remove name")

    name = context.args[0]
    users = load_users()
    uid = next((k for k, v in users.items() if v == name), None)
    if not uid:
        return update.message.reply_text("❌ User not found.")

    del users[uid]
    save_users(users)
    log_file = os.path.join(LOG_FOLDER, f"{name}.json")
    if os.path.exists(log_file):
        os.remove(log_file)

    update.message.reply_text(f"🗑 Removed user {name} (ID: {uid})")

def list_users(update: Update, context: CallbackContext):
    users = load_users()
    if not users:
        return update.message.reply_text("⚠️ No users added yet.")
    text = "👥 Tracked Users:\n\n"
    for uid, name in users.items():
        text += f"• {name} (ID: {uid})\n"
    update.message.reply_text(text)

def info(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        return update.message.reply_text("Usage: /info name")
    name = context.args[0]
    users = load_users()
    uid = next((k for k, v in users.items() if v == name), None)
    if not uid:
        return update.message.reply_text("❌ User not found.")

    session_path = os.path.join(LOG_FOLDER, f"{name}.json")
    if not os.path.exists(session_path):
        return update.message.reply_text("❌ No session data yet.")

    with open(session_path, 'r') as f:
        logs = json.load(f)

    sessions = []
    total_online = timedelta()
    first_seen = None
    is_online = False

    for i in range(0, len(logs) - 1, 2):
        start = datetime.strptime(logs[i]["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        end = datetime.strptime(logs[i + 1]["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        if not first_seen:
            first_seen = start
        duration = end - start
        total_online += duration
        sessions.append({
            "start": start.strftime("%m-%d %I:%M:%S %p"),
            "end": end.strftime("%m-%d %I:%M:%S %p"),
            "duration": str(duration)
        })

    if len(logs) % 2 != 0:
        is_online = True
        if not first_seen:
            first_seen = datetime.strptime(logs[0]["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)

    msg = f"📊 User Info: {name} (ID: {uid})\n\n"
    msg += f"👤 First tracked: {first_seen.strftime('%m-%d %H:%M:%S')} IST\n" if first_seen else "👤 First tracked: Unknown\n"
    msg += f"⏱ Total online time: {str(total_online)}\n\n"
    msg += f"Status: {'🟢 Currently online' if is_online else '🔴 Currently offline'}\n\n"
    msg += f"📅 Session History ({len(sessions)} sessions):\n"

    for i, s in enumerate(sessions[-20:], 1):
        msg += f"\n{i}) 🟢 {s['start']}\n   🔴 {s['end']}\n   ⏱ {s['duration']}"
    update.message.reply_text(msg)

def export(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        return update.message.reply_text("Usage: /export name")
    name = context.args[0]
    users = load_users()
    uid = next((k for k, v in users.items() if v == name), None)
    if not uid:
        return update.message.reply_text("❌ User not found.")

    session_path = os.path.join(LOG_FOLDER, f"{name}.json")
    if not os.path.exists(session_path):
        return update.message.reply_text("❌ No session data yet.")

    with open(session_path, 'r') as f:
        logs = json.load(f)

    sessions = []
    total_online = timedelta()
    first_seen = None

    for i in range(0, len(logs) - 1, 2):
        start = datetime.strptime(logs[i]["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        end = datetime.strptime(logs[i + 1]["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
        if not first_seen:
            first_seen = start
        duration = end - start
        total_online += duration
        sessions.append({
            "start": start.strftime("%m-%d %I:%M:%S %p"),
            "end": end.strftime("%m-%d %I:%M:%S %p"),
            "duration": str(duration)
        })

    report = f"📊 User Info: {name} (ID: {uid})\n\n"
    report += f"👤 First tracked: {first_seen.strftime('%m-%d %H:%M:%S')} IST\n" if first_seen else "👤 First tracked: Unknown\n"
    report += f"⏱ Total online time: {str(total_online)}\n\n"
    report += f"📅 Session History ({len(sessions)} sessions):\n\n"

    for i, s in enumerate(sessions[-20:], 1):
        report += f"{i}) 🟢 {s['start']}\n    🔴 {s['end']}\n    ⏱ {s['duration']}\n\n"

    export_path = f"{name}_session_report.txt"
    with open(export_path, 'w') as f:
        f.write(report.strip())

    update.message.reply_document(document=open(export_path, 'rb'), filename=export_path)
    os.remove(export_path)

# --- RENDER-FRIENDLY HTTP SERVER ---
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"✅ Telegram Spy Tracker bot is running on Render.")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()

# --- RUN EVERYTHING ---
if __name__ == "__main__":
    threading.Thread(target=run_http_server).start()
    main()