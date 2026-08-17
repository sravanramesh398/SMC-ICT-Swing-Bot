import requests
import time
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

# ==========================================
# ⚙️ 1. BOT CONFIGURATION & SETTINGS
# ==========================================
BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
CHAT_ID = "458226949"

# 9 Major & Cross Pairs
MAJOR_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

# Pair-specific SL buffers and thresholds
PAIR_CONFIG = {
    'EURUSD': {'buffer': 0.00150, 'min_sl': 0.00080, 'max_sl': 0.00350},
    'GBPUSD': {'buffer': 0.00250, 'min_sl': 0.00100, 'max_sl': 0.00400},
    'AUDUSD': {'buffer': 0.00150, 'min_sl': 0.00080, 'max_sl': 0.00350},
    'USDCAD': {'buffer': 0.00150, 'min_sl': 0.00080, 'max_sl': 0.00350},
    'NZDUSD': {'buffer': 0.00150, 'min_sl': 0.00080, 'max_sl': 0.00350},
    'USDJPY': {'buffer': 0.20,    'min_sl': 0.080,   'max_sl': 0.450},
    'EURJPY': {'buffer': 0.20,    'min_sl': 0.080,   'max_sl': 0.450},
    'GBPJPY': {'buffer': 0.25,    'min_sl': 0.100,   'max_sl': 0.500},
    'AUDJPY': {'buffer': 0.20,    'min_sl': 0.080,   'max_sl': 0.450},
}

DISPLACEMENT_THRESHOLD = 0.50  # Minimum 50% candle body for MSS confirmation

# ==========================================
# 📲 2. TELEGRAM ALERT DISPATCHER
# ==========================================
def send_telegram_alert(pair, direction, entry, sl, tp, step_details):
    """Sends 4-Step SMC Trade Alert"""
    if direction == "STARTUP":
        msg = f"""
🏛️ <b>SMC 4-STEP STRATEGY BOT ACTIVE</b> ✅
───────────────────────
1️⃣ <b>HTF Bias:</b> Daily/4H Trend & POI
2️⃣ <b>Liquidity:</b> PDH/PDL Sweep
3️⃣ <b>LTF Shift:</b> 15M/5M CHoCH (Body ≥ 50%)
4️⃣ <b>Entry:</b> Mitigation + Pure 1:2 RR
⏰ <b>Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST</code>
───────────────────────
<i>Institutional Order Flow Engine Live!</i>
"""
    else:
        dir_icon = "🟢 <b>BUY SETUP</b>" if direction == "BUY" else "🔴 <b>SELL SETUP</b>"
        msg = f"""
🚀 <b>SMC 4-STEP TRADE ALERT</b> 🚀
───────────────────────
📊 <b>Pair:</b> <code>{pair}</code>
🧭 <b>Action:</b> {dir_icon}
───────────────────────
💵 <b>Entry Price:</b> <code>{entry:.5f}</code>
🛑 <b>Stop Loss (SL):</b> <code>{sl:.5f}</code>
🎯 <b>Take Profit (1:2 RR):</b> <code>{tp:.5f}</code>
───────────────────────
📋 <b>4-STEP VERIFICATION:</b>
{step_details}
───────────────────────
💡 <b>Rule:</b> Move SL to Break-Even at +1 R profit.
⏰ <b>Time:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST</code>
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Send Error: {e}")

# ==========================================
# 📊 3. DATA FETCHER
# ==========================================
def get_data(symbol, interval):
    """Fetches real-time candle data via TradingView TA"""
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange="FOREXCOM",
            screener="forex",
            interval=interval
        )
        analysis = handler.get_analysis()
        return analysis.indicators
    except Exception as e:
        print(f"Fetch Error {symbol} on {interval}: {e}")
        return None

# ==========================================
# 🧠 4. CORE SMC SCANNER (THE 4 STEPS)
# ==========================================
def main():
    print("==================================================================")
    print("   🏛️ SMC 4-STEP STRATEGY SCANNER RUNNING")
    print("==================================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs...")

    # Send startup message
    send_telegram_alert("STATUS", "STARTUP", 0, 0, 0, "")

    for pair in MAJOR_PAIRS:
        try:
            # Multi-timeframe fetch: Daily (HTF Bias/Liquidity), 4H (POI), 15M (LTF Execution)
            d_ind = get_data(pair, Interval.INTERVAL_1_DAY)
            h4_ind = get_data(pair, Interval.INTERVAL_4_HOURS)
            m15_ind = get_data(pair, Interval.INTERVAL_15_MINUTES)

            if not d_ind or not h4_ind or not m15_ind:
                continue

            cfg = PAIR_CONFIG.get(pair, PAIR_CONFIG['EURUSD'])
            buffer = cfg['buffer']
            min_sl = cfg['min_sl']
            max_sl = cfg['max_sl']

            live_price = round(m15_ind["close"], 5)

            # -------------------------------------------------------------
            # STEP 1: HTF Trend & Bias (Daily / 4H)
            # -------------------------------------------------------------
            d_open = round(d_ind["open"], 5)
            d_close = round(d_ind["close"], 5)
            d_high = round(d_ind["high"], 5)    # PDH (Buy-side Liquidity)
            d_low = round(d_ind["low"], 5)      # PDL (Sell-side Liquidity)

            h4_open = round(h4_ind["open"], 5)
            h4_close = round(h4_ind["close"], 5)

            is_htf_bullish = (d_close >= d_open) or (h4_close >= h4_open)
            is_htf_bearish = (d_close <= d_open) or (h4_close <= h4_open)

            # -------------------------------------------------------------
            # STEP 2: Liquidity Sweep Verification
            # -------------------------------------------------------------
            # Sell-side Liquidity Sweep (Swept PDL and closed back above)
            m15_low = round(m15_ind["low"], 5)
            m15_high = round(m15_ind["high"], 5)
            m15_open = round(m15_ind["open"], 5)
            m15_close = round(m15_ind["close"], 5)

            swept_ssl = (m15_low <= d_low) and (live_price > d_low)
            swept_bsl = (m15_high >= d_high) and (live_price < d_high)

            # -------------------------------------------------------------
            # STEP 3: LTF Confirmation (CHoCH / MSS + 50% Displacement)
            # -------------------------------------------------------------
            range_15m = max(m15_high - m15_low, 0.00001)
            body_15m = abs(m15_close - m15_open)
            has_displacement = (body_15m / range_15m) >= DISPLACEMENT_THRESHOLD

            # -------------------------------------------------------------
            # STEP 4: Mitigation Entry & Pure 1:2 Risk Management
            # -------------------------------------------------------------
            # 🟢 BUY SETUP
            if is_htf_bullish and swept_ssl and (m15_close > m15_open) and has_displacement:
                sl = round(m15_low - buffer, 5)
                risk = round(live_price - sl, 5)

                if min_sl <= risk <= max_sl:
                    tp = round(live_price + (risk * 2.0), 5)
                    step_log = (
                        f"• <b>Step 1 (HTF):</b> Daily/4H Bullish Structure\n"
                        f"• <b>Step 2 (Sweep):</b> PDL Swept at <code>{d_low:.5f}</code>\n"
                        f"• <b>Step 3 (Shift):</b> 15M Bullish CHoCH (Body ≥ 50%)\n"
                        f"• <b>Step 4 (Entry):</b> Bullish Mitigation (Pure 1:2 RR)"
                    )
                    send_telegram_alert(pair, "BUY", live_price, sl, tp, step_log)
                    print(f"✅ Alert Sent: {pair} BUY (4-Step SMC Confirmed)")

            # 🔴 SELL SETUP
            elif is_htf_bearish and swept_bsl and (m15_close < m15_open) and has_displacement:
                sl = round(m15_high + buffer, 5)
                risk = round(sl - live_price, 5)

                if min_sl <= risk <= max_sl:
                    tp = round(live_price - (risk * 2.0), 5)
                    step_log = (
                        f"• <b>Step 1 (HTF):</b> Daily/4H Bearish Structure\n"
                        f"• <b>Step 2 (Sweep):</b> PDH Swept at <code>{d_high:.5f}</code>\n"
                        f"• <b>Step 3 (Shift):</b> 15M Bearish CHoCH (Body ≥ 50%)\n"
                        f"• <b>Step 4 (Entry):</b> Bearish Mitigation (Pure 1:2 RR)"
                    )
                    send_telegram_alert(pair, "SELL", live_price, sl, tp, step_log)
                    print(f"✅ Alert Sent: {pair} SELL (4-Step SMC Confirmed)")

            time.sleep(1.0)
        except Exception as e:
            print(f"Error scanning {pair}: {e}")
            continue

    print("✅ 4-Step SMC Scan finished successfully.")

if __name__ == "__main__":
    main()
