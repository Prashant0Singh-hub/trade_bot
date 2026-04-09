import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from signal_parser import parse_signal
import requests
import pytz
from datetime import datetime

# ⚠️ FILL THESE IN:
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
AUTH_TOKEN     = os.environ.get("AUTH_TOKEN", "")
ALGO_ID        = os.environ.get("ALGO_ID", "28925086")

def is_market_open():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    open_time  = now.replace(hour=9,  minute=15, second=0)
    close_time = now.replace(hour=15, minute=30, second=0)
    return open_time <= now <= close_time

def send_to_tradetron(signal):
    if not is_market_open():
        print("Market is closed. Signal skipped.")
        return

    url = "https://api.tradetron.tech/api"
    payload = {
        "auth-token": AUTH_TOKEN,
        "key":   "side",     "value":  signal.get("side", ""),
        "key1":  "symbol",   "value1": signal.get("symbol", ""),
        "key2":  "quantity", "value2": str(signal.get("quantity", 1)),
        "key3":  "sl",       "value3": str(signal.get("stop_loss", 0)),
        "key4":  "target",   "value4": str(signal.get("target", 0)),
    }
    response = requests.post(url, json=payload)
    print(f"Tradetron replied: {response.status_code} → {response.text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message and not update.channel_post:
        return
    message = update.message or update.channel_post
    if not message or not message.text:
        return
    text = message.text
    print(f"Message received: {text}")

    signal = parse_signal(text)

    if "side" in signal and "symbol" in signal:
        print(f"✅ Valid signal: {signal}")
        send_to_tradetron(signal)
    else:
        print("⚠️ Ignored — not a valid trade signal")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.UpdateType.CHANNEL_POSTS, handle_message))
    print("✅ Bot is running and listening...")
    app.run_polling()

if __name__ == "__main__":
    main()