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

def send_telegram_alert(pair, direction, entry, sl, tp1, tp2, sweep_level, details):
    """Sends Optimized SMC Swing Trade Alert with 1:2 & 1:3 RR Targets"""
    dir_icon = "🟢 *BUY (BULLISH REVERSAL)*" if direction == "BUY" else "🔴 *SELL (BEARISH REVERSAL)*"
    
    msg = f"""
🚀 *OPTIMIZED SMC SWING SETUP* 🚀
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Setup:* `Daily Liquidity Sweep + 1H MSS`
🧭 *Direction:* {dir_icon}
🎯 *Level Swept:* `{sweep_level}`
───────────────────────
💵 *Entry Price:* `{entry}`
🛑 *Stop Loss (SL):* `{sl}`
🎯 *Take Profit 1 (1:2 RR):* `{tp1}` *(Book 50% & Move SL to BE)*
🎯 *Take Profit 2 (1:3 RR):* `{tp2}` *(Runner Target)*
───────────────────────
📋 *SWING RULES:*
1️⃣ *Confirmation:* {details}
2️⃣ *Risk Rule:* Maximum 1% - 2% Risk per trade.
3️⃣ *Trade Mgmt:* Move SL to Entry (BE) as soon as TP1 is reached!
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
    print("   🤖 SMC OPTIMIZED SWING BOT (DAILY SWEEP + 1H MSS ENGINE)")
    print("==================================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs for High-Probability Swing Setups...")

    for pair in MAJOR_PAIRS:
        try:
            # Multi-Timeframe Data (Daily & 1H)
            d_ind = get_data(pair, Interval.INTERVAL_1_DAY)
            h1_ind = get_data(pair, Interval.INTERVAL_1_HOUR)

            if not d_ind or not h1_ind:
                continue

            live_price = round(h1_ind["close"], 5)
            pdh = round(d_ind["high"], 5)
            pdl = round(d_ind["low"], 5)

            high_1h = round(h1_ind["high"], 5)
            low_1h = round(h1_ind["low"], 5)
            close_1h = round(h1_ind["close"], 5)

            # Pip Buffers
            pip_buffer = 0.20 if "JPY" in pair else 0.00150
            min_risk = 0.10 if "JPY" in pair else 0.00100
            max_risk = 0.50 if "JPY" in pair else 0.00500

            # -------------------------------------------------------------
            # 1. BULLISH SWING: PDL SWEEP + 1H MSS (BUY)
            # -------------------------------------------------------------
            if live_price > pdl and low_1h <= pdl and close_1h > high_1h * 0.9995:
                sl = round(low_1h - pip_buffer, 5)
                risk = round(live_price - sl, 5)

                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price + (risk * 2.0), 5)
                    tp2 = round(live_price + (risk * 3.0), 5)
                    
                    send_telegram_alert(
                        pair=pair,
                        direction="BUY",
                        entry=live_price,
                        sl=sl,
                        tp1=tp1,
                        tp2=tp2,
                        sweep_level=pdl,
                        details="PDL swept on 1H with strong Bullish Structure Shift"
                    )
                    print(f"✅ Bullish Swing Alert Sent: {pair}")

            # -------------------------------------------------------------
            # 2. BEARISH SWING: PDH SWEEP + 1H MSS (SELL)
            # -------------------------------------------------------------
            elif live_price < pdh and high_1h >= pdh and close_1h < low_1h * 1.0005:
                sl = round(high_1h + pip_buffer, 5)
                risk = round(sl - live_price, 5)

                if min_risk <= risk <= max_risk:
                    tp1 = round(live_price - (risk * 2.0), 5)
                    tp2 = round(live_price - (risk * 3.0), 5)

                    send_telegram_alert(
                        pair=pair,
                        direction="SELL",
                        entry=live_price,
                        sl=sl,
                        tp1=tp1,
                        tp2=tp2,
                        sweep_level=pdh,
                        details="PDH swept on 1H with strong Bearish Structure Shift"
                    )
                    print(f"✅ Bearish Swing Alert Sent: {pair}")

            time.sleep(1.0)
        except Exception as e:
            print(f"Error on {pair}: {e}")
            continue

    print("✅ Swing scan completed successfully.")

if __name__ == "__main__":
    main()
