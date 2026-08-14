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

def send_telegram_alert(pair, engine_name, direction, entry, sl, tp, trend, model):
    """Sends SMC Swing Trade Telegram Alert"""
    icon = "🟢 *BUY SETUP*" if direction == "BUY" else "🔴 *SELL SETUP*"
    
    msg = f"""
🚀 *SMC SWING TRADE ALERT* 🚀
───────────────────────
📊 *Pair:* `{pair}`
⚡ *Engine:* `{engine_name}`
🧭 *Direction:* {icon}
📈 *Trend Bias:* `{trend}`
───────────────────────
💵 *Entry Price:* `{entry}`
🛑 *Stop Loss (SL):* `{sl}`
🎯 *Take Profit (TP):* `{tp}`
📊 *Model:* `{model}`
───────────────────────
⏰ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
💡 *Swing Rule:* Target HTF Key Levels / Liquidity!
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
    print("   🤖 SMC PRO SWING BOT (MULTI-TIMEFRAME ENGINE RUNNING)")
    print("==================================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')} IST] Scanning 9 Pairs for Swing Setups...")

    for pair in MAJOR_PAIRS:
        try:
            # Multi-Timeframe Data
            d_ind = get_data(pair, Interval.INTERVAL_1_DAY)
            h4_ind = get_data(pair, Interval.INTERVAL_4_HOURS)
            h1_ind = get_data(pair, Interval.INTERVAL_1_HOUR)
            m15_ind = get_data(pair, Interval.INTERVAL_15_MINUTES)

            if not d_ind or not h4_ind or not h1_ind or not m15_ind:
                continue

            live_price = round(m15_ind["close"], 5)
            
            # --- HTF DAILY BIAS ---
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

            pip_buffer = 0.25 if "JPY" in pair else 0.00250

            # -------------------------------------------------------------
            # ENGINE 1: DAILY SETUP + 1H STRUCTURE SHIFT
            # -------------------------------------------------------------
            # Engine 1 Buy: Daily Low Sweep + 1H Shift
            if live_price > pdl and h1_ind["low"] <= pdl and close_1h > high_1h * 0.9995:
                sl = round(low_1h - pip_buffer, 5)
                tp = round(pdh, 5)
                send_telegram_alert(pair, "ENGINE 1 (Daily + 1H)", "BUY", live_price, sl, tp, daily_trend, "Daily Sweep + 1H MSS")

            # Engine 1 Sell: Daily High Sweep + 1H Shift
            elif live_price < pdh and h1_ind["high"] >= pdh and close_1h < low_1h * 1.0005:
                sl = round(high_1h + pip_buffer, 5)
                tp = round(pdl, 5)
                send_telegram_alert(pair, "ENGINE 1 (Daily + 1H)", "SELL", live_price, sl, tp, daily_trend, "Daily Sweep + 1H MSS")

            # -------------------------------------------------------------
            # ENGINE 2: 4H DISCOUNT/PREMIUM + 15M ENTRY SHIFT
            # -------------------------------------------------------------
            # Engine 2 Buy: Bullish Trend + 4H Discount Zone (<50%) + 15M Shift
            if daily_trend == "BULLISH" and live_price < eq_4h and close_15m > open_15m and m15_ind["high"] >= high_1h * 0.9995:
                sl = round(low_4h - pip_buffer, 5)
                tp = round(high_4h, 5)
                send_telegram_alert(pair, "ENGINE 2 (4H + 15M)", "BUY", live_price, sl, tp, daily_trend, "4H Discount + 15M MSS")

            # Engine 2 Sell: Bearish Trend + 4H Premium Zone (>50%) + 15M Shift
            elif daily_trend == "BEARISH" and live_price > eq_4h and close_15m < open_15m and m15_ind["low"] <= low_1h * 1.0005:
                sl = round(high_4h + pip_buffer, 5)
                tp = round(low_4h, 5)
                send_telegram_alert(pair, "ENGINE 2 (4H + 15M)", "SELL", live_price, sl, tp, daily_trend, "4H Premium + 15M MSS")

            time.sleep(1.0)
        except Exception as e:
            print(f"Error on {pair}: {e}")
            continue

    print("✅ Swing scan completed successfully.")

if __name__ == "__main__":
    main()
