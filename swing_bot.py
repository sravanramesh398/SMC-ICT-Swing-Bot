import requests
import time
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

# --- BOT CONFIGURATION ---
BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
CHAT_ID = "458226949"

# 9 Major & Cross Pairs
MAJOR_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

def send_telegram_alert(pair, engine_name, direction, entry, sl, tp1, tp2, level_info, details):
    """Sends SMC Dual-Engine Swing Trade Telegram Alert"""
    if direction == "STARTUP":
        msg = f"""
🤖 *SMC DUAL-ENGINE SWING BOT ACTIVE* ✅
───────────────────────
⚙️ *Engine 1:* `Daily Sweep + 1H MSS (1:2 & 1:3 RR)`
⚙️ *Engine 2:* `4H Discount/Premium + 15M MSS (1:2 & 1:3 RR)`
⏰ *Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST`
🎯 *Status:* Scanning 9 Pairs for High-Probability Setups...
"""
    else:
        dir_icon = "🟢 *BUY SETUP*" if direction == "BUY" else "🔴 *SELL SETUP*"
        msg = f"""
🚀 *SMC SWING TRADE ALERT* 🚀
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Engine:* `{engine_name}`
🧭 *Direction:* {dir_icon}
🎯 *Zone/Level:* `{level_info}`
───────────────────────
💵 *Entry Price:* `{entry}`
🛑 *Stop Loss (SL):* `{sl}`
🎯 *Take Profit 1 (1:2 RR):* `{tp1}` *(Book 50% & Move SL to BE)*
🎯 *Take Profit 2 (1:3 RR):* `{tp2}` *(Runner Target)*
───────────────────────
📋 *CONFIRMATION:* {details}
💡 *Management:* Move SL to Entry (Break-Even) immediately when TP1 is hit!
───────────────────────
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Send Error: {e}")

def get_data(symbol, interval):
    """Safely fetch market data using TradingView TA"""
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

def main():
    print("==================================================================")
    print("   🤖 SMC DUAL-ENGINE SWING BOT (ENGINE 1 & ENGINE 2 RUNNING)")
    print("==================================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs for Setups...")

    # Startup Ping
    send_telegram_alert("STATUS", "Dual Engine", "STARTUP", 0, 0, 0, 0, "N/A", "Active")

    for pair in MAJOR_PAIRS:
        try:
            # Multi-Timeframe Data (Daily, 4H, 1H, 15M)
            d_ind = get_data(pair, Interval.INTERVAL_1_DAY)
            h4_ind = get_data(pair, Interval.INTERVAL_4_HOURS)
            h1_ind = get_data(pair, Interval.INTERVAL_1_HOUR)
            m15_ind = get_data(pair, Interval.INTERVAL_15_MINUTES)

            if not d_ind or not h4_ind or not h1_ind or not m15_ind:
                continue

            live_price = round(m15_ind["close"], 5)
            
            # --- HTF DAILY DATA ---
            daily_ema20 = d_ind.get("EMA20", d_ind["close"])
            daily_trend = "BULLISH" if d_ind["close"] >= daily_ema20 else "BEARISH"
            pdh = round(d_ind["high"], 5)
            pdl = round(d_ind["low"], 5)

            # --- 4H DATA ---
            high_4h = round(h4_ind["high"], 5)
            low_4h = round(h4_ind["low"], 5)
            eq_4h = round(low_4h + (high_4h - low_4h) * 0.5, 5)

            # --- 1H / 15M DATA ---
            high_1h = round(h1_ind["high"], 5)
            low_1h = round(h1_ind["low"], 5)
            close_1h = round(h1_ind["close"], 5)
            
            open_15m = round(m15_ind["open"], 5)
            close_15m = round(m15_ind["close"], 5)
            high_15m = round(m15_ind["high"], 5)
            low_15m = round(m15_ind["low"], 5)

            # Pip Buffers & Risk Limits
            pip_buffer = 0.20 if "JPY" in pair else 0.00150
            min_risk = 0.10 if "JPY" in pair else 0.00100
            max_risk = 0.50 if "JPY" in pair else 0.00500

            # =============================================================
            # 1. ENGINE 1: DAILY SWEEP + 1H STRUCTURE SHIFT
            # =============================================================
            # Engine 1 Buy (PDL Sweep)
            if live_price > pdl and low_1h <= pdl and close_1h > high_1h * 0.9995:
                sl = round(low_1h - pip_buffer, 5)
                risk = round(live_price - sl, 5)
                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price + (risk * 2.0), 5)
                    tp2 = round(live_price + (risk * 3.0), 5)
                    send_telegram_alert(pair, "ENGINE 1 (Daily Sweep + 1H MSS)", "BUY", live_price, sl, tp1, tp2, f"PDL ({pdl})", "PDL swept with 1H Bullish Shift")
                    print(f"✅ Alert Sent: {pair} ENGINE 1 BUY")

            # Engine 1 Sell (PDH Sweep)
            elif live_price < pdh and high_1h >= pdh and close_1h < low_1h * 1.0005:
                sl = round(high_1h + pip_buffer, 5)
                risk = round(sl - live_price, 5)
                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price - (risk * 2.0), 5)
                    tp2 = round(live_price - (risk * 3.0), 5)
                    send_telegram_alert(pair, "ENGINE 1 (Daily Sweep + 1H MSS)", "SELL", live_price, sl, tp1, tp2, f"PDH ({pdh})", "PDH swept with 1H Bearish Shift")
                    print(f"✅ Alert Sent: {pair} ENGINE 1 SELL")

            # =============================================================
            # 2. ENGINE 2: 4H DISCOUNT/PREMIUM + 15M MSS (TREND-ALIGNED)
            # =============================================================
            # Engine 2 Buy: Daily Bullish + 4H Discount Zone (<50%) + 15M Shift
            if daily_trend == "BULLISH" and live_price < eq_4h and close_15m > open_15m and high_15m >= high_1h * 0.9995:
                sl = round(low_4h - pip_buffer, 5)
                risk = round(live_price - sl, 5)
                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price + (risk * 2.0), 5)
                    tp2 = round(live_price + (risk * 3.0), 5)
                    send_telegram_alert(pair, "ENGINE 2 (4H Discount + 15M MSS)", "BUY", live_price, sl, tp1, tp2, f"4H Discount EQ ({eq_4h})", "Bullish Trend + 4H Discount Rejection + 15M Shift")
                    print(f"✅ Alert Sent: {pair} ENGINE 2 BUY")

            # Engine 2 Sell: Daily Bearish + 4H Premium Zone (>50%) + 15M Shift
            elif daily_trend == "BEARISH" and live_price > eq_4h and close_15m < open_15m and low_15m <= low_1h * 1.0005:
                sl = round(high_4h + pip_buffer, 5)
                risk = round(sl - live_price, 5)
                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price - (risk * 2.0), 5)
                    tp2 = round(live_price - (risk * 3.0), 5)
                    send_telegram_alert(pair, "ENGINE 2 (4H Premium + 15M MSS)", "SELL", live_price, sl, tp1, tp2, f"4H Premium EQ ({eq_4h})", "Bearish Trend + 4H Premium Rejection + 15M Shift")
                    print(f"✅ Alert Sent: {pair} ENGINE 2 SELL")

            time.sleep(1.0)
        except Exception as e:
            print(f"Error on {pair}: {e}")
            continue

    print("✅ Dual-Engine scan completed successfully.")

if __name__ == "__main__":
    main()
