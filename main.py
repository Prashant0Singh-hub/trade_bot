import os
import requests
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from signal_parser import parse_signal, is_valid_signal, format_signal_summary

# ============================================
# CONFIGURATION — set these in Railway Variables
# ============================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
AUTH_TOKEN     = os.environ.get("AUTH_TOKEN", "")
ALGO_ID        = os.environ.get("ALGO_ID", "")

def is_market_open():
    """Returns True if NSE/BSE market is open (Mon-Fri, 9:15 AM - 3:30 PM IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.weekday() >= 5:  # Saturday or Sunday
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

    # ── EXIT ALL ──────────────────────────────────────────────
    if signal.get('action') == 'EXIT_ALL':
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "action",  "value":  "EXIT_ALL"
        }
        print("🚪 Sending EXIT ALL signal")

    # ── EXIT single position ──────────────────────────────────
    elif signal.get('action') == 'EXIT':
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "action",       "value":  "EXIT",
            "key1":  "symbol",       "value1": signal.get("symbol", ""),
            "key2":  "strike",       "value2": str(signal.get("strike", "")),
            "key3":  "option_type",  "value3": signal.get("option_type", ""),
        }
        print(f"🚪 Sending EXIT signal: {signal.get('symbol')} {signal.get('strike','')} {signal.get('option_type','')}")

    # ── OPTIONS entry ─────────────────────────────────────────
    elif "option_type" in signal:
        # Determine strike value to send
        if "strike" in signal:
            strike_value = str(signal["strike"])
        elif signal.get("strike_type") == "ATM":
            offset = signal.get("atm_offset", 0)
            strike_value = f"ATM{'+' + str(offset) if offset > 0 else str(offset) if offset < 0 else ''}"
        else:
            strike_value = "ATM"

        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "side",         "value":  signal.get("side", ""),
            "key1":  "symbol",       "value1": signal.get("symbol", ""),
            "key2":  "strike",       "value2": strike_value,
            "key3":  "option_type",  "value3": signal.get("option_type", ""),
            "key4":  "quantity",     "value4": str(signal.get("quantity", 1)),
            "key5":  "sl",           "value5": str(signal.get("stop_loss", 0)),
            "key6":  "target",       "value6": str(signal.get("target", 0)),
            "key7":  "target2",      "value7": str(signal.get("target2", 0)),
            "key8":  "entry_price",  "value8": str(signal.get("entry_price", 0)),
        }

    # ── CASH STOCK entry ──────────────────────────────────────
    else:
        payload = {
            "auth-token": AUTH_TOKEN,
            "key":   "side",     "value":  signal.get("side", ""),
            "key1":  "symbol",   "value1": signal.get("symbol", ""),
            "key2":  "quantity", "value2": str(signal.get("quantity", 1)),
            "key3":  "sl",       "value3": str(signal.get("stop_loss", 0)),
            "key4":  "target",   "value4": str(signal.get("target", 0)),
            "key5":  "target2",  "value5": str(signal.get("target2", 0)),
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"✅ Tradetron replied: {response.status_code} → {response.text}")
        if response.status_code != 200:
            print(f"⚠️  Payload sent: {payload}")
    except requests.exceptions.Timeout:
        print("❌ Error: Tradetron request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Tradetron")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages from channel or private chat"""
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

            # Warnings for missing optional fields
            if signal.get('action') == 'ENTRY':
                if 'stop_loss' not in signal:
                    print("⚠️  No stop loss in message")
                if 'target' not in signal:
                    print("⚠️  No target in message")
                if 'quantity' not in signal:
                    print("⚠️  No quantity — defaulting to 1")

            send_to_tradetron(signal)

        else:
            print("⚠️  Ignored — not a valid trade signal")

    except Exception as e:
        print(f"❌ Error processing message: {e}")


def main():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN not set! Check Railway Variables.")
        return
    if not AUTH_TOKEN:
        print("❌ AUTH_TOKEN not set! Check Railway Variables.")
        return
    if not ALGO_ID:
        print("❌ ALGO_ID not set! Check Railway Variables.")
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
