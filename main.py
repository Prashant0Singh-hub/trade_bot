import os
import requests
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from signal_parser import parse_signal, is_valid_signal

# ============================================
# CONFIGURATION — set these in Railway Variables
# ============================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
AUTH_TOKEN     = os.environ.get("AUTH_TOKEN", "")
ALGO_ID        = os.environ.get("ALGO_ID", "28925086")

def is_market_open():
    """Returns True if NSE market is open (Mon-Fri, 9:15 AM - 3:30 PM IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= now <= close_time

def send_to_tradetron(signal):
    """Send parsed signal to Tradetron API"""
    if not is_market_open():
        print("⏰ Market is closed. Signal skipped.")
        return

    url = "https://api.tradetron.tech/api"

    # Handle EXIT signals
    if signal.get('action') == 'EXIT':
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "side",   "value":  "EXIT",
            "key1":  "symbol", "value1": signal.get("symbol", ""),
        }
        print(f"🚪 Sending EXIT signal for {signal.get('symbol')}")
    else:
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "side",     "value":  signal.get("side", ""),
            "key1":  "symbol",   "value1": signal.get("symbol", ""),
            "key2":  "quantity", "value2": str(signal.get("quantity", 1)),
            "key3":  "sl",       "value3": str(signal.get("stop_loss", 0)),
            "key4":  "target",   "value4": str(signal.get("target", 0)),
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"✅ Tradetron replied: {response.status_code} → {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Error: Tradetron request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Tradetron")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages"""
    if not update.message and not update.channel_post:
        return

    message = update.message or update.channel_post
    if not message or not message.text:
        return

    text = message.text.strip()
    print(f"\n📨 Message received: {text}")

    try:
        signal = parse_signal(text)

        if signal.get('action') == 'EXIT' and 'symbol' in signal:
            print(f"🚪 Exit signal detected: {signal}")
            send_to_tradetron(signal)

        elif is_valid_signal(signal):
            print(f"✅ Valid entry signal: {signal}")

            # Warn if optional fields are missing
            if 'stop_loss' not in signal:
                print("⚠️  Warning: No stop loss detected in message")
            if 'target' not in signal:
                print("⚠️  Warning: No target detected in message")
            if 'quantity' not in signal:
                print("⚠️  Warning: No quantity detected — defaulting to 1")

            send_to_tradetron(signal)

        else:
            print("⚠️  Ignored — not a valid trade signal")

    except Exception as e:
        print(f"❌ Error processing message: {e}")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN not set!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND) | filters.UpdateType.CHANNEL_POSTS,
        handle_message
    ))
    print("✅ Bot is running and listening...")
    app.run_polling()

if __name__ == "__main__":
    main()
