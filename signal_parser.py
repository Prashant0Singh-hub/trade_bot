import re

def parse_signal(message):
    """
    ============================================
    SUPPORTED FORMATS:
    ============================================
    BUY NIFTY 24000 CE SL:50 T1:150 T2:250 QTY:50
    SELL NIFTY 23700 PE 47 SL:55 T1:30 T2:25 QTY:5
    BUY SENSEX 76600 CE GOOD ABOVE 660 SL:597 T1:700 T2:750 QTY:4
    BUY NIFTY 23750 CE GOOD ABOVE 55 SL:36 T1:67 T2:85 QTY:1
    BUY NIFTY ATM CE SL:50 T1:150 QTY:50
    BUY NIFTY ATM+100 CE SL:50 T1:150 QTY:50
    EXIT NIFTY 24000 CE
    EXIT ALL / CLOSE ALL
    BUY RELIANCE SL:2400 T1:2500 T2:2600 QTY:10
    ============================================
    """

    signal = {}
    msg_upper = message.strip().upper()

    # ── EXIT ALL ──────────────────────────────────────────────
    if re.search(r'\b(EXIT ALL|CLOSE ALL|SQUARE OFF ALL)\b', msg_upper):
        signal['action'] = 'EXIT_ALL'
        return signal

    # ── EXIT single position ──────────────────────────────────
    exit_match = re.search(r'\b(EXIT|CLOSE)\b', msg_upper)
    if exit_match:
        signal['action'] = 'EXIT'
        exit_symbol = re.search(
            r'\b(?:EXIT|CLOSE)\s+(BANKNIFTY|NIFTY|FINNIFTY|SENSEX|MIDCPNIFTY|[A-Z]{2,20})',
            msg_upper
        )
        if exit_symbol:
            signal['symbol'] = exit_symbol.group(1)
        # Detect strike for exit (e.g. EXIT NIFTY 24000 CE)
        strike_match = re.search(r'\b(\d{4,6})\b', msg_upper)
        if strike_match:
            signal['strike'] = int(strike_match.group(1))
        opt_type = re.search(r'\b(CE|PE|CALL|PUT)\b', msg_upper)
        if opt_type:
            signal['option_type'] = 'CE' if opt_type.group(1) in ('CE', 'CALL') else 'PE'
        return signal

    # ── BUY / SELL side ───────────────────────────────────────
    side = re.search(r'\b(BUY|SELL)\b', msg_upper)
    if side:
        signal['side'] = side.group(1)

    # ── Underlying symbol ─────────────────────────────────────
    symbol = re.search(
        r'\b(BANKNIFTY|NIFTY|FINNIFTY|SENSEX|MIDCPNIFTY|'
        r'RELIANCE|TATAMOTORS|HDFCBANK|INFY|TCS|WIPRO|SBIN|'
        r'ICICIBANK|AXISBANK|KOTAKBANK|BAJFINANCE|ADANIENT|'
        r'HINDUNILVR|ITC|LT|MARUTI|ONGC|NTPC|POWERGRID|'
        r'SUNPHARMA|TITAN|ULTRACEMCO|ASIANPAINT)\b',
        msg_upper
    )
    if symbol:
        signal['symbol'] = symbol.group(1)

    # ── Option type CE / PE ───────────────────────────────────
    opt_type = re.search(r'\b(CE|PE|CALL|PUT)\b', msg_upper)
    if opt_type:
        signal['option_type'] = 'CE' if opt_type.group(1) in ('CE', 'CALL') else 'PE'

    # ── Strike price ──────────────────────────────────────────
    # ATM offset format: ATM+100, ATM-100
    atm_offset = re.search(r'\bATM([+-]\d+)?\b', msg_upper)
    if atm_offset:
        signal['strike_type'] = 'ATM'
        offset = atm_offset.group(1)
        signal['atm_offset'] = int(offset) if offset else 0
    else:
        # Numeric strike: must be 4-6 digits and look like a real strike
        # We look for it AFTER the symbol name and BEFORE/AFTER CE/PE
        # Strategy: find all 4-6 digit numbers and pick the first one
        # that is NOT the SL, T1, T2, QTY value
        # We extract strike early, before removing keywords
        strike_candidates = re.findall(r'\b(\d{4,6})\b', msg_upper)
        if strike_candidates:
            signal['strike'] = int(strike_candidates[0])

    # ── Remove noise phrases before parsing numbers ───────────
    # "GOOD ABOVE 660" → the 660 is an entry price hint, not SL/T1
    # We tag it as entry_price and remove to avoid confusion
    good_above = re.search(r'GOOD\s+ABOVE\s+(\d+\.?\d*)', msg_upper)
    if good_above:
        signal['entry_price'] = float(good_above.group(1))
        # Remove this phrase so numbers don't get mis-parsed
        msg_upper = re.sub(r'GOOD\s+ABOVE\s+\d+\.?\d*', '', msg_upper)

    # ── Stop Loss ─────────────────────────────────────────────
    sl = re.search(r'\bSL[:\s]?(\d+\.?\d*)', msg_upper)
    if sl:
        signal['stop_loss'] = float(sl.group(1))

    # ── Target 1 ─────────────────────────────────────────────
    t1 = re.search(r'\b(?:T1|TGT|TARGET)[:\s]?(\d+\.?\d*)', msg_upper)
    if t1:
        signal['target'] = float(t1.group(1))

    # ── Target 2 ─────────────────────────────────────────────
    t2 = re.search(r'\bT2[:\s]?(\d+\.?\d*)', msg_upper)
    if t2:
        signal['target2'] = float(t2.group(1))

    # ── Quantity ──────────────────────────────────────────────
    qty = re.search(r'\b(?:QTY|LOT|LOTS|QT)[:\s]?(\d+)', msg_upper)
    if qty:
        signal['quantity'] = int(qty.group(1))

    # ── Default action ────────────────────────────────────────
    signal['action'] = 'ENTRY'

    return signal


def is_valid_signal(signal):
    """Signal is valid if it has minimum required fields."""
    if signal.get('action') == 'EXIT_ALL':
        return True
    if signal.get('action') == 'EXIT' and 'symbol' in signal:
        return True
    return 'side' in signal and 'symbol' in signal


def format_signal_summary(signal):
    """Human-readable summary of parsed signal."""
    action = signal.get('action', 'ENTRY')

    if action == 'EXIT_ALL':
        return "EXIT ALL positions"

    if action == 'EXIT':
        return (
            f"EXIT {signal.get('symbol','')} "
            f"{signal.get('strike','')} "
            f"{signal.get('option_type','')}"
        ).strip()

    parts = [
        signal.get('side', ''),
        signal.get('symbol', ''),
        str(signal.get('strike', signal.get('strike_type', ''))),
        signal.get('option_type', ''),
    ]
    summary = ' '.join(p for p in parts if p)

    if 'entry_price' in signal:
        summary += f" ABOVE {signal['entry_price']}"
    if 'stop_loss' in signal:
        summary += f" SL:{signal['stop_loss']}"
    if 'target' in signal:
        summary += f" T1:{signal['target']}"
    if 'target2' in signal:
        summary += f" T2:{signal['target2']}"
    if 'quantity' in signal:
        summary += f" QTY:{signal['quantity']}"

    return summary


# ── Self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    test_messages = [
        "BUY NIFTY 24000 CE SL:50 T1:150 T2:250 QTY:50",
        "BUY SENSEX 76600 CE GOOD ABOVE 660 SL:597 T1:700 T2:750 QTY:4",
        "BUY NIFTY 23750 CE GOOD ABOVE 55 SL:36 T1:67 T2:85 QTY:1",
        "SELL NIFTY 23700 PE 47 SL:55 T1:30 T2:25 QTY:5",
        "BUY NIFTY ATM CE SL:50 T1:150 QTY:50",
        "BUY NIFTY ATM+100 CE SL:50 T1:150 QTY:50",
        "BUY RELIANCE SL:2400 T1:2500 T2:2600 QTY:10",
        "EXIT NIFTY 24000 CE",
        "EXIT ALL",
        "CLOSE ALL",
        "Hey what's the market like today?",
        "SELL BANKNIFTY 52000 PE SL:200 T1:500 T2:800 QTY:1",
    ]

    print(f"{'MESSAGE':<55} {'RESULT'}")
    print("-" * 110)
    for msg in test_messages:
        result = parse_signal(msg)
        valid = is_valid_signal(result)
        summary = format_signal_summary(result) if valid else "❌ IGNORED"
        print(f"{msg:<55} {summary}")
        if valid:
            print(f"  → Raw: {result}")
        print()
