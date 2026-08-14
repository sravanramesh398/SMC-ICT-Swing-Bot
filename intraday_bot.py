import requests
import time
from datetime import datetime, timezone, timedelta
from tradingview_ta import TA_Handler, Interval

# --- BOT CONFIGURATION ---
BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
CHAT_ID = "458226949"

PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

def send_telegram_alert(pair, setup_title, session_name, direction, entry, sl, tp1, tp2, sweep_level, details):
    """Sends Pro SMC Intraday Alert with Full Execution Rules & Risk Management"""
    if direction == "SCAN":
        message = f"🤖 *JARVIS SMC BOT IS LIVE & SCANNING* ✅\n───────────────────────\n🏛️ *Active Session:* `{session_name}`\n⏰ *Scan Time:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST`\n📊 *Monitoring:* 9 Major & Cross Forex Pairs\n───────────────────────\n_Waiting for High Probability Liquidity Sweeps..._"
    else:
        dir_icon = "🟢 *BUY (BULLISH REVERSAL)*" if direction == "BUY" else "🔴 *SELL (BEARISH REVERSAL)*"
        message = f"""
🔥 *INTRADAY SMC SNIPER SETUP* 🔥
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Setup:* {setup_title}
🧭 *Direction:* {dir_icon}
🏛️ *Session:* `{session_name}`
🎯 *Level Swept:* `{sweep_level}`
───────────────────────
💵 *Execution Price:* `{entry}`
🛑 *Stop Loss (SL):* `{sl}`
🎯 *TP 1 (1:2 RR):* `{tp1}` *(Shift SL to Break-Even here)*
🎯 *TP 2 (1:3+ RR / Target):* `{tp2}`
───────────────────────
📋 *EXECUTION RULES:*
1️⃣ *Confirmation:* {details}
2️⃣ *Entry:* Wait for 5M/1M MSS & Enter on FVG retracement.
3️⃣ *Risk Rule:* Maximum 1% - 2% Risk per trade.
4️⃣ *Trade Mgmt:* Move SL to Entry when TP1 is hit.
───────────────────────
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
    print("   🤖 SMC INTRADAY BOT WITH COMPLETE 3-RULE EXECUTION ENGINE")
    print("==================================================================")
    
    session = get_current_killzone()
    now_str = datetime.now().strftime('%H:%M:%S')
    print(f"[{now_str} IST] Active Zone: {session} | Scanning 9 Pairs...")

    # Heartbeat / Startup ping to confirm Telegram connection is active
    send_telegram_alert("STATUS", "BOT RUNNING", session, "SCAN", 0, 0, 0, 0, "N/A", "")

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

        # JPY pairs vs Standard pip buffer
        buffer = 0.15 if "JPY" in pair else 0.00150

        # -------------------------------------------------------------
        # RULE 1 & 2: PDH SWEEP + BODY REJECTION (SELL SHORT)
        # -------------------------------------------------------------
        if high >= pdh and price < pdh:
            sl = round(high + buffer, 5)
            risk = abs(sl - price)
            tp1 = round(price - (risk * 2), 5)
            tp2 = round(price - (risk * 3), 5)
            
            print(f"🚨 {pair} Swept PDH with Rejection Body!")
            send_telegram_alert(
                pair=pair,
                setup_title="PDH LIQUIDITY PURGED 🔴 (BEARISH REVERSAL)",
                session_name=session,
                direction="SELL",
                entry=price,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                sweep_level=pdh,
                details="15M Wick swept PDH, candle closed inside (Bearish MSS shift)"
            )

        # -------------------------------------------------------------
        # RULE 1 & 2: PDL SWEEP + BODY REJECTION (BUY LONG)
        # -------------------------------------------------------------
        elif low <= pdl and price > pdl:
            sl = round(low - buffer, 5)
            risk = abs(price - sl)
            tp1 = round(price + (risk * 2), 5)
            tp2 = round(price + (risk * 3), 5)

            print(f"🚨 {pair} Swept PDL with Rejection Body!")
            send_telegram_alert(
                pair=pair,
                setup_title="PDL LIQUIDITY PURGED 🟢 (BULLISH REVERSAL)",
                session_name=session,
                direction="BUY",
                entry=price,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                sweep_level=pdl,
                details="15M Wick swept PDL, candle closed inside (Bullish MSS shift)"
            )

        # -------------------------------------------------------------
        # RULE 3: KILLZONE HIGH/LOW SWEEP WITH SESSION LIQUIDITY
        # -------------------------------------------------------------
        elif "Killzone" in session:
            # Killzone High Sweep (SELL)
            if high >= pdh * 0.9997 and price < open_p:
                sl = round(high + buffer, 5)
                risk = abs(sl - price)
                tp1 = round(price - (risk * 2), 5)
                tp2 = round(price - (risk * 3), 5)

                send_telegram_alert(
                    pair=pair,
                    setup_title=f"{session.split()[0]} HIGH SWEEP 🔴",
                    session_name=session,
                    direction="SELL",
                    entry=price,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    sweep_level=high,
                    details="Killzone High swept with Bearish Rejection Close"
                )

            # Killzone Low Sweep (BUY)
            elif low <= pdl * 1.0003 and price > open_p:
                sl = round(low - buffer, 5)
                risk = abs(price - sl)
                tp1 = round(price + (risk * 2), 5)
                tp2 = round(price + (risk * 3), 5)

                send_telegram_alert(
                    pair=pair,
                    setup_title=f"{session.split()[0]} LOW SWEEP 🟢",
                    session_name=session,
                    direction="BUY",
                    entry=price,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    sweep_level=low,
                    details="Killzone Low swept with Bullish Rejection Close"
                )

        time.sleep(1.0)

    print("✅ Scan cycle finished successfully.")

if __name__ == "__main__":
    main()
