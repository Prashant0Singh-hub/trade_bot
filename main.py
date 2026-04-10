import os
import requests
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from signal_parser import parse_signal, is_valid_signal, format_signal_summary

# ============================================
# CONFIGURATION
# ============================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
AUTH_TOKEN     = os.environ.get("AUTH_TOKEN", "")
ALGO_ID        = os.environ.get("ALGO_ID", "28925086")

def is_market_open():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.weekday() >= 5:
        return False
    open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= now <= close_time

def send_to_tradetron(signal):
    if not is_market_open():
        print("⏰ Market closed. Signal skipped.")
        return

    url = "https://api.tradetron.tech/api"

    # EXIT ALL
    if signal.get('action') == 'EXIT_ALL':
        payload = {
            "auth-token": AUTH_TOKEN,
            "key": "action", "value": "EXIT_ALL"
        }

    # EXIT single position
    elif signal.get('action') == 'EXIT':
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":  "action",      "value":  "EXIT",
            "key1": "symbol",      "value1": signal.get("symbol", ""),
            "key2": "strike",      "value2": str(signal.get("strike", "")),
            "key3": "option_type", "value3": signal.get("option_type", ""),
        }

    # ENTRY — Options
    elif "strike" in signal or "strike_type" in signal:
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":  "side",        "value":  signal.get("side", ""),
            "key1": "symbol",      "value1": signal.get("symbol", ""),
            "key2": "strike",      "value2": str(signal.get("strike", signal.get("strike_type", "ATM"))),
            "key3": "atm_offset",  "value3": str(signal.get("atm_offset", 0)),
            "key4": "option_type", "value4": signal.get("option_type", ""),
            "key5": "expiry",      "value5": signal.get("expiry", ""),
            "key6": "quantity",    "value6": str(signal.get("quantity", 50)),
            "key7": "sl",          "value7": str(signal.get("stop_loss", 0)),
            "key8": "target",      "value8": str(signal.get("target", 0)),
        }

    # ENTRY — Cash stocks
    else:
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":  "side",     "value":  signal.get("side", ""),
            "key1": "symbol",   "value1": signal.get("symbol", ""),
            "key2": "quantity", "value2": str(signal.get("quantity", 1)),
            "key3": "sl",       "value3": str(signal.get("stop_loss", 0)),
            "key4": "target",   "value4": str(signal.get("target", 0)),
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
    if not update.message and not update.channel_post:
        return
    message = update.message or update.channel_post
    if not message or not message.text:
        return

    text = message.text.strip()
    print(f"\n📨 Message received: {text}")

    try:
        signal = parse_signal(text)

        if is_valid_signal(signal):
            summary = format_signal_summary(signal)
            print(f"✅ Valid signal: {summary}")
            print(f"   Raw: {signal}")

            if 'stop_loss' not in signal:
                print("⚠️  No stop loss detected")
            if 'target' not in signal:
                print("⚠️  No target detected")
            if 'quantity' not in signal and signal.get('action') not in ['EXIT_ALL']:
                print("⚠️  No quantity detected — using default")

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
