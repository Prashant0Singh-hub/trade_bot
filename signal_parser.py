import re

def parse_signal(message):
    signal = {}

    # Detect BUY or SELL
    side = re.search(r'\b(BUY|SELL)\b', message.upper())
    if side:
        signal['side'] = side.group(1)

    # Detect stock symbol (word after BUY/SELL)
    symbol = re.search(r'\b(?:BUY|SELL)\s+([A-Z]+)', message.upper())
    if symbol:
        signal['symbol'] = symbol.group(1)

    # Detect Stop Loss
    sl = re.search(r'SL[:\s](\d+\.?\d*)', message.upper())
    if sl:
        signal['stop_loss'] = float(sl.group(1))

    # Detect Target
    t1 = re.search(r'T1[:\s](\d+\.?\d*)', message.upper())
    if t1:
        signal['target'] = float(t1.group(1))

    # Detect Quantity
    qty = re.search(r'QTY[:\s](\d+)', message.upper())
    if qty:
        signal['quantity'] = int(qty.group(1))

    return signal