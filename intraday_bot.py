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

def send_telegram_alert(pair, setup_title, session_name, sweep_level, current_price, details):
    """Sends Clean SMC Intraday Alert with Killzone & Body Rejection Confirmation"""
    message = f"""
🔥 *INTRADAY SMC SETUP* 🔥
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Setup:* {setup_title}
🏛️ *Session / Killzone:* `{session_name}`
🎯 *Level Swept:* `{sweep_level}`
💵 *Current Price:* `{current_price}`
───────────────────────
🔍 *Confirmation:* `{details}`
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
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

def get_current_killzone():
    """Returns active ICT Killzone (Feature 1)"""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour

    # London Killzone (07:00 - 10:00 UTC | 12:30 PM - 03:30 PM IST)
    if 7 <= hour < 10:
        return "London Killzone 🇬🇧"
    # New York Killzone (12:00 - 15:00 UTC | 05:30 PM - 08:30 PM IST)
    elif 12 <= hour < 15:
        return "New York Killzone 🇺🇸"
    # Asian Session Range
    elif 0 <= hour < 7:
        return "Asian Session 🇯🇵"
    else:
        return "Regular Trading Hours"

def get_pair_analysis(symbol):
    try:
        # Daily Data
        h_daily = TA_Handler(symbol=symbol, exchange="FOREXCOM", screener="forex", interval=Interval.INTERVAL_1_DAY).get_analysis()
        pdh = round(h_daily.indicators["high"], 5)
        pdl = round(h_daily.indicators["low"], 5)

        time.sleep(0.8)

        # 15M Data (For Sweep & Candle Body Rejection Confirmation)
        h_15m = TA_Handler(symbol=symbol, exchange="FOREXCOM", screener="forex", interval=Interval.INTERVAL_15_MINUTES).get_analysis()
        live_price = round(h_15m.indicators["close"], 5)
        open_15m = round(h_15m.indicators["open"], 5)
        high_15m = round(h_15m.indicators["high"], 5)
        low_15m = round(h_15m.indicators["low"], 5)

        return {
            "symbol": symbol,
            "price": live_price,
            "open": open_15m,
            "high": high_15m,
            "low": low_15m,
            "pdh": pdh,
            "pdl": pdl
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def main():
    print("==================================================================")
    print("   🤖 SMC INTRADAY BOT (KILLZONES + CANDLE REJECTION / MSS)")
    print("==================================================================")
    
    session = get_current_killzone()
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Active Zone: {session} | Scanning 9 Pairs...")

    for pair in PAIRS:
        data = get_pair_analysis(pair)
        if not data:
            continue

        price = data["price"]
        open_p = data["open"]
        high = data["high"]
        low = data["low"]
        pdh = data["pdh"]
        pdl = data["pdl"]

        # -------------------------------------------------------------
        # 1. PDH SWEEP + BODY REJECTION (BEARISH REVERSAL)
        # High swept above PDH, but Candle Closed BELOW PDH (Wick Sweep)
        # -------------------------------------------------------------
        if high >= pdh and price < pdh:
            print(f"🚨 {pair} Swept PDH with Rejection Body!")
            send_telegram_alert(
                pair=pair,
                setup_title="PDH LIQUIDITY PURGED 🔴 (BEARISH REJECTION)",
                session_name=session,
                sweep_level=pdh,
                current_price=price,
                details="15M Wick swept High, but body closed back below PDH (MSS shift potential)"
            )

        # -------------------------------------------------------------
        # 2. PDL SWEEP + BODY REJECTION (BULLISH REVERSAL)
        # Low swept below PDL, but Candle Closed ABOVE PDL (Wick Sweep)
        # -------------------------------------------------------------
        elif low <= pdl and price > pdl:
            print(f"🚨 {pair} Swept PDL with Rejection Body!")
            send_telegram_alert(
                pair=pair,
                setup_title="PDL LIQUIDITY PURGED 🟢 (BULLISH REJECTION)",
                session_name=session,
                sweep_level=pdl,
                current_price=price,
                details="15M Wick swept Low, but body closed back above PDL (MSS shift potential)"
            )

        # -------------------------------------------------------------
        # 3. KILLZONE HIGH/LOW SWEEP (Inside London/NY Killzones)
        # -------------------------------------------------------------
        elif "Killzone" in session:
            # High Sweep during Killzone with Bearish Close
            if high >= pdh * 0.9997 and price < open_p:
                send_telegram_alert(
                    pair=pair,
                    setup_title=f"{session.split()[0]} HIGH SWEEP 🔴",
                    session_name=session,
                    sweep_level=high,
                    current_price=price,
                    details="Killzone High swept with Bearish Candle Close rejection"
                )
            # Low Sweep during Killzone with Bullish Close
            elif low <= pdl * 1.0003 and price > open_p:
                send_telegram_alert(
                    pair=pair,
                    setup_title=f"{session.split()[0]} LOW SWEEP 🟢",
                    session_name=session,
                    sweep_level=low,
                    current_price=price,
                    details="Killzone Low swept with Bullish Candle Close rejection"
                )

        time.sleep(1.0)

    print("✅ Scan cycle finished successfully.")

if __name__ == "__main__":
    main()
