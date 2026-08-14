import requests
import time
from datetime import datetime, timezone
from tradingview_ta import TA_Handler, Interval

# --- BOT CONFIGURATION ---
BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
CHAT_ID = "458226949"

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

def send_telegram_alert(pair, sweep_type, sweep_level, current_price):
    """Sends Instant Telegram Alert for Sweeps"""
    message = f"""
🔥 *INTRADAY SET UP* 🔥
───────────────────────
📊 *Pair:* {pair}
⚡ *Alert:* {sweep_type}
🎯 *Sweep Level:* `{sweep_level}`
💵 *Current Price:* `{current_price}`
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
───────────────────────
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Send Error: {e}")

def get_pair_analysis(symbol):
    try:
        # Daily Data
        h_daily = TA_Handler(symbol=symbol, exchange="FOREXCOM", screener="forex", interval=Interval.INTERVAL_1_DAY).get_analysis()
        pdh = round(h_daily.indicators["high"], 5)
        pdl = round(h_daily.indicators["low"], 5)

        time.sleep(1.0)

        # 15M Data
        h_15m = TA_Handler(symbol=symbol, exchange="FOREXCOM", screener="forex", interval=Interval.INTERVAL_15_MINUTES).get_analysis()
        live_price = round(h_15m.indicators["close"], 5)
        high_15m = round(h_15m.indicators["high"], 5)
        low_15m = round(h_15m.indicators["low"], 5)

        return {
            "symbol": symbol,
            "price": live_price,
            "pdh": pdh,
            "pdl": pdl,
            "high_15m": high_15m,
            "low_15m": low_15m
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def main():
    print("==================================================================")
    print("   🤖 SMC INTRADAY SCANNER RUNNING VIA GITHUB ACTIONS")
    print("==================================================================")
    
    now_utc = datetime.now(timezone.utc)
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs...")

    for pair in PAIRS:
        data = get_pair_analysis(pair)
        if not data:
            continue

        price = data["price"]
        pdh = data["pdh"]
        pdl = data["pdl"]
        high_15m = data["high_15m"]
        low_15m = data["low_15m"]

        # 1. PDH / PDL SWEEPS
        if high_15m >= pdh:
            print(f"🚨 {pair} Swept PDH ({pdh})!")
            send_telegram_alert(pair, "PREVIOUS DAY HIGH (PDH) SWEPT 🔴", pdh, price)

        elif low_15m <= pdl:
            print(f"🚨 {pair} Swept PDL ({pdl})!")
            send_telegram_alert(pair, "PREVIOUS DAY LOW (PDL) SWEPT 🟢", pdl, price)

        # 2. SESSION SWEEPS (London / NY)
        elif 7 <= now_utc.hour < 12:
            if high_15m >= pdh * 0.9995:
                send_telegram_alert(pair, "ASIAN HIGH LIQUIDITY SWEPT 🔴", high_15m, price)
            elif low_15m <= pdl * 1.0005:
                send_telegram_alert(pair, "ASIAN LOW LIQUIDITY SWEPT 🟢", low_15m, price)

        elif 12 <= now_utc.hour < 18:
            if high_15m >= pdh * 0.9998:
                send_telegram_alert(pair, "LONDON HIGH LIQUIDITY SWEPT 🔴", high_15m, price)
            elif low_15m <= pdl * 1.0002:
                send_telegram_alert(pair, "LONDON LOW LIQUIDITY SWEPT 🟢", low_15m, price)

        time.sleep(1.2)

    print("✅ Scan cycle finished successfully.")

if __name__ == "__main__":
    main()
