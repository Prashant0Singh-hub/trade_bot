import re

"""
============================================
UNIVERSAL NIFTY OPTIONS SIGNAL PARSER
============================================
Supports ALL of these formats:

Type 1 - Simple:
  BUY NIFTY 24000 CE QTY:50
  SELL NIFTY 23500 PE QTY:50

Type 2 - With Expiry:
  BUY NIFTY 24000 CE 17APR2026 QTY:50

Type 3 - With SL and Target:
  BUY NIFTY 24000 CE SL:50 T1:150 QTY:50

Type 4 - Full Detail:
  BUY NIFTY 24000 CE 17APR2026 SL:50 T1:150 QTY:2LOT

Type 5 - Short Indian Format:
  NIFTY 24000CE BUY SL50 TGT150

Type 6 - ATM Format:
  BUY NIFTY ATM CE QTY:50
  BUY NIFTY ATM+100 CE QTY:50
  BUY NIFTY ATM-100 PE QTY:50

Type 7 - Exit:
  EXIT NIFTY 24000 CE
  CLOSE ALL
  EXIT ALL
============================================
"""

def parse_signal(message):
    signal = {}
    message = message.strip()
    msg_upper = message.upper()

    # ─────────────────────────────────────
    # EXIT / CLOSE detection
    # ─────────────────────────────────────
    if re.search(r'\b(EXIT|CLOSE)\s+ALL\b', msg_upper):
        return {'action': 'EXIT_ALL'}

    exit_match = re.search(r'\b(EXIT|CLOSE)\b', msg_upper)
    if exit_match:
        signal['action'] = 'EXIT'
        # Try to extract what to exit
        symbol_after = re.search(r'\b(?:EXIT|CLOSE)\s+(NIFTY|BANKNIFTY|SENSEX|FINNIFTY)', msg_upper)
        if symbol_after:
            signal['symbol'] = symbol_after.group(1)
        strike_exit = re.search(r'(\d{4,6})\s*(CE|PE)', msg_upper)
        if strike_exit:
            signal['strike'] = int(strike_exit.group(1))
            signal['option_type'] = strike_exit.group(2)
        return signal

    # ─────────────────────────────────────
    # BUY / SELL detection
    # ─────────────────────────────────────
    side = re.search(r'\b(BUY|SELL)\b', msg_upper)
    if side:
        signal['side'] = side.group(1)
        signal['action'] = 'ENTRY'

    # ─────────────────────────────────────
    # Underlying symbol (NIFTY, BANKNIFTY etc.)
    # ─────────────────────────────────────
    symbol = re.search(r'\b(BANKNIFTY|NIFTY|FINNIFTY|SENSEX|MIDCPNIFTY)\b', msg_upper)
    if symbol:
        signal['symbol'] = symbol.group(1)

    # ─────────────────────────────────────
    # ATM format detection (Type 6)
    # BUY NIFTY ATM CE, BUY NIFTY ATM+100 CE, BUY NIFTY ATM-100 PE
    # ─────────────────────────────────────
    atm_match = re.search(r'\bATM\s*([+-]\s*\d+)?\b', msg_upper)
    if atm_match:
        signal['strike_type'] = 'ATM'
        offset_str = atm_match.group(1)
        if offset_str:
            signal['atm_offset'] = int(offset_str.replace(' ', ''))
        else:
            signal['atm_offset'] = 0

    # ─────────────────────────────────────
    # Strike price (24000, 23500 etc.)
    # Handles both "24000 CE" and "24000CE"
    # ─────────────────────────────────────
    if 'strike_type' not in signal:
        strike = re.search(r'\b(\d{4,6})\s*(CE|PE)\b', msg_upper)
        if strike:
            signal['strike'] = int(strike.group(1))
            signal['option_type'] = strike.group(2)
        else:
            # Handles "24000CE" without space
            strike2 = re.search(r'(\d{4,6})(CE|PE)', msg_upper)
            if strike2:
                signal['strike'] = int(strike2.group(1))
                signal['option_type'] = strike2.group(2)
    else:
        # ATM format - get CE/PE
        opt_type = re.search(r'\b(CE|PE)\b', msg_upper)
        if opt_type:
            signal['option_type'] = opt_type.group(1)

    # ─────────────────────────────────────
    # Expiry date detection
    # Handles: 17APR2026, 17-APR-2026, 17/04/2026
    # ─────────────────────────────────────
    expiry = re.search(
        r'\b(\d{1,2}[\-/]?(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\-/]?\d{2,4})\b',
        msg_upper
    )
    if expiry:
        signal['expiry'] = expiry.group(1)

    # ─────────────────────────────────────
    # Stop Loss
    # Handles: SL:50, SL 50, SL50
    # ─────────────────────────────────────
    sl = re.search(r'\bSL[:\s]?(\d+\.?\d*)', msg_upper)
    if sl:
        signal['stop_loss'] = float(sl.group(1))

    # ─────────────────────────────────────
    # Target
    # Handles: T1:150, TGT:150, TARGET:150, TGT150
    # ─────────────────────────────────────
    tgt = re.search(r'\b(?:T1|TGT|TARGET)[:\s]?(\d+\.?\d*)', msg_upper)
    if tgt:
        signal['target'] = float(tgt.group(1))

    # ─────────────────────────────────────
    # Quantity / Lots
    # Handles: QTY:50, QTY50, 2LOT, LOT:2, LOTS:2
    # ─────────────────────────────────────
    qty = re.search(r'\b(?:QTY|QUANTITY)[:\s]?(\d+)', msg_upper)
    if qty:
        signal['quantity'] = int(qty.group(1))
    else:
        lot = re.search(r'(\d+)\s*LOT[S]?', msg_upper)
        if lot:
            signal['lots'] = int(lot.group(1))
            signal['quantity'] = int(lot.group(1)) * 50  # 1 NIFTY lot = 50
        else:
            lot2 = re.search(r'\bLOT[S]?[:\s]?(\d+)', msg_upper)
            if lot2:
                signal['lots'] = int(lot2.group(1))
                signal['quantity'] = int(lot2.group(1)) * 50

    return signal


def is_valid_signal(signal):
    """
    A signal is valid if it has:
    - A side (BUY/SELL) or action (EXIT)
    - A symbol (NIFTY etc.)
    - An option type (CE/PE) or ATM strike type
    """
    if signal.get('action') in ['EXIT_ALL']:
        return True
    if signal.get('action') == 'EXIT' and 'symbol' in signal:
        return True
    has_side = 'side' in signal
    has_symbol = 'symbol' in signal
    has_option = 'option_type' in signal
    return has_side and has_symbol and has_option


def format_signal_summary(signal):
    """Returns a human readable summary of the parsed signal"""
    if signal.get('action') == 'EXIT_ALL':
        return "EXIT ALL positions"

    if signal.get('action') == 'EXIT':
        strike_info = f" {signal.get('strike', '')}{signal.get('option_type', '')}" if 'strike' in signal else ""
        return f"EXIT {signal.get('symbol', '')}{strike_info}"

    side = signal.get('side', '?')
    symbol = signal.get('symbol', '?')

    if signal.get('strike_type') == 'ATM':
        offset = signal.get('atm_offset', 0)
        offset_str = f"+{offset}" if offset > 0 else str(offset) if offset < 0 else ""
        strike_str = f"ATM{offset_str}"
    else:
        strike_str = f"{signal.get('strike', '?')}"

    opt_type = signal.get('option_type', '?')
    expiry = f" EXP:{signal.get('expiry')}" if 'expiry' in signal else ""
    sl = f" SL:{signal.get('stop_loss')}" if 'stop_loss' in signal else ""
    tgt = f" T1:{signal.get('target')}" if 'target' in signal else ""

    if 'lots' in signal:
        qty_str = f" {signal.get('lots')}LOT ({signal.get('quantity')} qty)"
    elif 'quantity' in signal:
        qty_str = f" QTY:{signal.get('quantity')}"
    else:
        qty_str = ""

    return f"{side} {symbol} {strike_str} {opt_type}{expiry}{sl}{tgt}{qty_str}"


# ─────────────────────────────────────
# TEST ALL FORMATS
# ─────────────────────────────────────
if __name__ == "__main__":
    test_messages = [
        # Type 1 - Simple
        "BUY NIFTY 24000 CE QTY:50",
        "SELL NIFTY 23500 PE QTY:50",

        # Type 2 - With Expiry
        "BUY NIFTY 24000 CE 17APR2026 QTY:50",

        # Type 3 - With SL and Target
        "BUY NIFTY 24000 CE SL:50 T1:150 QTY:50",

        # Type 4 - Full Detail
        "BUY NIFTY 24000 CE 17APR2026 SL:50 T1:150 QTY:2LOT",

        # Type 5 - Short Indian Format
        "NIFTY 24000CE BUY SL50 TGT150",

        # Type 6 - ATM Format
        "BUY NIFTY ATM CE QTY:50",
        "BUY NIFTY ATM+100 CE QTY:50",
        "BUY NIFTY ATM-100 PE QTY:50",

        # Type 7 - Exit
        "EXIT NIFTY 24000 CE",
        "CLOSE ALL",
        "EXIT ALL",

        # BANKNIFTY
        "BUY BANKNIFTY 52000 CE SL:100 T1:300 QTY:1LOT",

        # Malformed - should be ignored
        "Hey what's the market today?",
        "NIFTY looking bullish today",
    ]

    print("=" * 60)
    print("UNIVERSAL PARSER TEST RESULTS")
    print("=" * 60)

    for msg in test_messages:
        signal = parse_signal(msg)
        valid = is_valid_signal(signal)
        summary = format_signal_summary(signal) if valid else "IGNORED"
        status = "✅" if valid else "⚠️ "
        print(f"\n{status} Input:  {msg}")
        print(f"   Output: {summary}")
        if valid:
            print(f"   Raw:    {signal}")
