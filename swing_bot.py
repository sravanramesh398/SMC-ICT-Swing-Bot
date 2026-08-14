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

def send_telegram_alert(pair, engine_name, direction, entry, sl, tp, zone_info, details):
    """Sends SMC Pure 1:2 RR Swing Trade Alert with Displacement Filters"""
    if direction == "STARTUP":
        msg = f"""
🏛️ *SMC DUAL-ENGINE (PURE 1:2 RR) ACTIVE* ✅
───────────────────────
⚙️ *ENGINE 1:* `Daily Deep FVG (28%/72%) ➔ 1H MSS (Body ≥ 50%)`
⚙️ *ENGINE 2:* `4H Deep FVG (28%/72%) ➔ 15M MSS (Body ≥ 50%)`
🎯 *Target:* `Fixed 1:2 RR Target`
⏰ *Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST`
───────────────────────
_High-Probability Institutional Setup Live!_
"""
    else:
        dir_icon = "🟢 *BUY SETUP*" if direction == "BUY" else "🔴 *SELL SETUP*"
        msg = f"""
🚀 *SMC TRADE ALERT (PURE 1:2 RR)* 🚀
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Engine:* `{engine_name}`
🧭 *Direction:* {dir_icon}
🎯 *Extreme Zone:* `{zone_info}`
───────────────────────
💵 *Entry Price:* `{entry}`
🛑 *Stop Loss (SL):* `{sl}`
🎯 *Take Profit (1:2 RR):* `{tp}`
───────────────────────
📋 *CONFIRMATION:* {details}
💡 *Management:* Pure 1:2 Risk to Reward Target.
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
    print("   🏛️ SMC PURE 1:2 RR DUAL-ENGINE BOT (BODY >= 50% ACTIVE)")
    print("==================================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs for High-Probability Setups...")

    # Startup Ping
    send_telegram_alert("STATUS", "Pure 1:2 Dual Engine", "STARTUP", 0, 0, 0, "N/A", "Active")

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
            
            # --- DAILY DEEP EXTREME ZONES (<= 28% & >= 72%) ---
            d_high = round(d_ind["high"], 5)
            d_low = round(d_ind["low"], 5)
            daily_discount = live_price <= d_low + (d_high - d_low) * 0.28
            daily_premium = live_price >= d_low + (d_high - d_low) * 0.72

            # --- 4-HOUR DEEP EXTREME ZONES (<= 28% & >= 72%) ---
            h4_high = round(h4_ind["high"], 5)
            h4_low = round(h4_ind["low"], 5)
            h4_discount = live_price <= h4_low + (h4_high - h4_low) * 0.28
            h4_premium = live_price >= h4_low + (h4_high - h4_low) * 0.72

            # --- 1-HOUR DATA & DISPLACEMENT ---
            high_1h = round(h1_ind["high"], 5)
            low_1h = round(h1_ind["low"], 5)
            open_1h = round(h1_ind["open"], 5)
            close_1h = round(h1_ind["close"], 5)
            
            range_1h = max(high_1h - low_1h, 0.00001)
            body_1h = abs(close_1h - open_1h)
            disp_1h = (body_1h / range_1h) >= 0.50

            # --- 15-MINUTE DATA & DISPLACEMENT ---
            high_15m = round(m15_ind["high"], 5)
            low_15m = round(m15_ind["low"], 5)
            open_15m = round(m15_ind["open"], 5)
            close_15m = round(m15_ind["close"], 5)
            
            range_15m = max(high_15m - low_15m, 0.00001)
            body_15m = abs(close_15m - open_15m)
            disp_15m = (body_15m / range_15m) >= 0.50

            # Pip Buffers & Risk Limits
            pip_buffer_h1 = 0.20 if "JPY" in pair else 0.00150
            pip_buffer_m15 = 0.15 if "JPY" in pair else 0.00100
            min_risk = 0.08 if "JPY" in pair else 0.00080
            max_risk = 0.50 if "JPY" in pair else 0.00500

            # =============================================================
            # 1. ENGINE 1: DAILY DEEP FVG ➔ 1H MSS + DISPLACEMENT
            # =============================================================
            if daily_discount and close_1h > open_1h and high_1h >= (d_high * 0.9995) and disp_1h:
                sl = round(low_1h - pip_buffer_h1, 5)
                risk = round(live_price - sl, 5)
                if min_risk <= risk <= max_risk:
                    tp = round(live_price + (risk * 2.0), 5)
                    send_telegram_alert(pair, "ENGINE 1 (Daily Deep FVG)", "BUY", live_price, sl, tp, f"Daily Extreme Discount ({d_low})", "Daily Deep FVG (<=28%) ➔ 1H Bullish MSS + Body ≥ 50%")
                    print(f"✅ Alert Sent: {pair} ENGINE 1 BUY")

            elif daily_premium and close_1h < open_1h and low_1h <= (d_low * 1.0005) and disp_1h:
                sl = round(high_1h + pip_buffer_h1, 5)
                risk = round(sl - live_price, 5)
                if min_risk <= risk <= max_risk:
                    tp = round(live_price - (risk * 2.0), 5)
                    send_telegram_alert(pair, "ENGINE 1 (Daily Deep FVG)", "SELL", live_price, sl, tp, f"Daily Extreme Premium ({d_high})", "Daily Deep FVG (>=72%) ➔ 1H Bearish MSS + Body ≥ 50%")
                    print(f"✅ Alert Sent: {pair} ENGINE 1 SELL")

            # =============================================================
            # 2. ENGINE 2: 4H DEEP FVG ➔ 15M MSS + DISPLACEMENT
            # =============================================================
            elif h4_discount and close_15m > open_15m and high_15m >= (h4_low + (h4_high - h4_low) * 0.22) and disp_15m:
                sl = round(low_15m - pip_buffer_m15, 5)
                risk = round(live_price - sl, 5)
                if min_risk <= risk <= max_risk:
                    tp = round(live_price + (risk * 2.0), 5)
                    send_telegram_alert(pair, "ENGINE 2 (4H Deep FVG)", "BUY", live_price, sl, tp, f"4H Extreme Discount ({h4_low})", "4H Deep FVG (<=28%) ➔ 15M Bullish MSS + Body ≥ 50%")
                    print(f"✅ Alert Sent: {pair} ENGINE 2 BUY")

            elif h4_premium and close_15m < open_15m and low_15m <= (h4_low + (h4_high - h4_low) * 0.78) and disp_15m:
                sl = round(high_15m + pip_buffer_m15, 5)
                risk = round(sl - live_price, 5)
                if min_risk <= risk <= max_risk:
                    tp = round(live_price - (risk * 2.0), 5)
                    send_telegram_alert(pair, "ENGINE 2 (4H Deep FVG)", "SELL", live_price, sl, tp, f"4H Extreme Premium ({h4_high})", "4H Deep FVG (>=72%) ➔ 15M Bearish MSS + Body ≥ 50%")
                    print(f"✅ Alert Sent: {pair} ENGINE 2 SELL")

            time.sleep(1.0)
        except Exception as e:
            print(f"Error on {pair}: {e}")
            continue

    print("✅ Pure 1:2 RR Dual-Engine scan completed successfully.")

if __name__ == "__main__":
    main()
