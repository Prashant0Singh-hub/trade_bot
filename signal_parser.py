import re

def parse_signal(message):
    """
    ============================================
    HOW TO EDIT THIS PARSER FOR YOUR FORMAT
    ============================================
    Current supported format:
      BUY RELIANCE SL:2400 T1:2500 QTY:10
      SELL NIFTY SL:22000 T1:21800 QTY:5

    To change the format, edit the regex patterns below:
    - side_pattern    → detects BUY or SELL
    - symbol_pattern  → detects stock name (word after BUY/SELL)
    - sl_pattern      → detects stop loss (after SL: or SL )
    - target_pattern  → detects target (after T1: or T1 )
    - qty_pattern     → detects quantity (after QTY: or QTY )

    Example: if your channel sends "RELIANCE BUY TGT:2500 STOPLOSS:2400 LOT:10"
    just update the patterns to match that format.
    ============================================
    """

    signal = {}
    message = message.strip()

    # Detect BUY or SELL
    side = re.search(r'\b(BUY|SELL)\b', message.upper())
    if side:
        signal['side'] = side.group(1)

    # Detect stock symbol (word after BUY/SELL)
    symbol = re.search(r'\b(?:BUY|SELL)\s+([A-Z]+)', message.upper())
    if symbol:
        signal['symbol'] = symbol.group(1)

    # Detect Stop Loss (SL:2400 or SL 2400)
    sl = re.search(r'SL[:\s](\d+\.?\d*)', message.upper())
    if sl:
        signal['stop_loss'] = float(sl.group(1))

    # Detect Target (T1:2500 or TGT:2500 or TARGET:2500)
    t1 = re.search(r'(?:T1|TGT|TARGET)[:\s](\d+\.?\d*)', message.upper())
    if t1:
        signal['target'] = float(t1.group(1))

    # Detect Quantity (QTY:10 or QTY 10 or LOT:10)
    qty = re.search(r'(?:QTY|LOT)[:\s](\d+)', message.upper())
    if qty:
        signal['quantity'] = int(qty.group(1))

    # Detect EXIT command (e.g. "EXIT RELIANCE" or "CLOSE RELIANCE")
    exit_match = re.search(r'\b(EXIT|CLOSE)\b', message.upper())
    if exit_match:
        signal['action'] = 'EXIT'
        exit_symbol = re.search(r'\b(?:EXIT|CLOSE)\s+([A-Z]+)', message.upper())
        if exit_symbol:
            signal['symbol'] = exit_symbol.group(1)
    else:
        signal['action'] = 'ENTRY'

    return signal


def is_valid_signal(signal):
    """Check if signal has minimum required fields"""
    return 'side' in signal and 'symbol' in signal
