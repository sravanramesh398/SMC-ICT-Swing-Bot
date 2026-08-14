import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timezone, timedelta

MAJOR_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

TELEGRAM_BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
TELEGRAM_CHAT_ID = "458226949"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def fetch_today_high_impact_news():
    try:
        response = requests.get("https://raw.githubusercontent.com/s4m33r/forex-factory-calendar/main/data/today.json", timeout=5)
        if response.status_code == 200:
            events = response.json()
            high_impact_times = []
            for ev in events:
                if ev.get('impact') in ['High', 'Red']:
                    ev_date_str = ev.get('date')
                    if ev_date_str:
                        ev_dt = datetime.fromisoformat(ev_date_str.replace('Z', '+00:00'))
                        high_impact_times.append(ev_dt)
            return high_impact_times
    except Exception:
        pass
    return []

def is_dynamic_news_pause_active():
    now_utc = datetime.now(timezone.utc)
    news_times = fetch_today_high_impact_news()
    for n_time in news_times:
        if (n_time - timedelta(minutes=30)) <= now_utc <= (n_time + timedelta(minutes=30)):
            return True, f"High Impact News Event at {n_time.strftime('%H:%M UTC')}"

    if (now_utc.hour == 13) or (now_utc.hour == 14 and now_utc.minute <= 15):
        return True, "US Market Opening / Economic Release Window"

    return False, ""

def scan_market():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_news_active, news_reason = is_dynamic_news_pause_active()
    if is_news_active:
        print(f"⚠️ Market Scanning Paused! Reason: {news_reason}")
        return

    for pair in MAJOR_PAIRS:
        try:
            ticker = f"{pair}=X"
            df_daily = yf.Ticker(ticker).history(period="60d", interval="1d")
            df_1h = yf.Ticker(ticker).history(period="10d", interval="1h")
            df_15m = yf.Ticker(ticker).history(period="5d", interval="15m")

            if df_daily.empty or df_1h.empty or df_15m.empty or len(df_daily) < 20:
                continue

            df_4h_res = df_1h.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
            }).dropna()

            live_price = round(df_15m['Close'].iloc[-1], 5)

            # Trend & Levels
            daily_ema20 = df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
            daily_trend = "BULLISH" if df_daily['Close'].iloc[-1] > daily_ema20 else "BEARISH"

            high_20 = df_daily['High'].iloc[-21:-1].max()
            low_20 = df_daily['Low'].iloc[-21:-1].min()
            eq_50 = low_20 + (high_20 - low_20) * 0.50
            pdh = df_daily['High'].iloc[-2]
            pdl = df_daily['Low'].iloc[-2]

            curr_close_1h = df_1h['Close'].iloc[-1]
            recent_1h_high = df_1h['High'].iloc[-4:-1].max()
            recent_1h_low = df_1h['Low'].iloc[-4:-1].min()
            buffer_1h = 0.50 if "JPY" in pair else 0.00400

            is_daily_bull_fvg = df_daily['High'].iloc[-4] < df_daily['Low'].iloc[-2] if len(df_daily) >= 4 else False
            is_daily_bear_fvg = df_daily['Low'].iloc[-4] > df_daily['High'].iloc[-2] if len(df_daily) >= 4 else False

            # Engine 1 Buy
            daily_buy_sweep = (live_price < eq_50 and pdl < df_daily['Low'].iloc[-10:-2].min())
            daily_buy_fvg = (is_daily_bull_fvg and live_price <= df_daily['Low'].iloc[-2] and live_price >= df_daily['High'].iloc[-4])

            if (daily_buy_sweep or daily_buy_fvg) and curr_close_1h > recent_1h_high:
                sl_val = round(df_1h['Low'].iloc[-4:].min() - buffer_1h, 5)
                tp_val = round(high_20, 5)
                model_used = "Daily FVG Tap + 1H MSS" if daily_buy_fvg else "Daily Sweep + 1H MSS"
                msg = f"🚀 *ENGINE 1: SWING (BUY)*\n\n🔹 *Pair:* `{pair}`\n🟢 *Entry:* `{live_price}`\n🔴 *SL:* `{sl_val}`\n🎯 *TP:* `{tp_val}`\n📊 *Model:* `{model_used}`\n🧭 *Trend:* `{daily_trend}`\n⏰ *Time:* `{now}` IST"
                send_telegram(msg)

            # Engine 1 Sell
            daily_sell_sweep = (live_price > eq_50 and pdh > df_daily['High'].iloc[-10:-2].max())
            daily_sell_fvg = (is_daily_bear_fvg and live_price >= df_daily['High'].iloc[-2] and live_price <= df_daily['Low'].iloc[-4])

            if (daily_sell_sweep or daily_sell_fvg) and curr_close_1h < recent_1h_low:
                sl_val = round(df_1h['High'].iloc[-4:].max() + buffer_1h, 5)
                tp_val = round(low_20, 5)
                model_used = "Daily FVG Tap + 1H MSS" if daily_sell_fvg else "Daily Sweep + 1H MSS"
                msg = f"🔻 *ENGINE 1: SWING (SELL)*\n\n🔹 *Pair:* `{pair}`\n🟢 *Entry:* `{live_price}`\n🔴 *SL:* `{sl_val}`\n🎯 *TP:* `{tp_val}`\n📊 *Model:* `{model_used}`\n🧭 *Trend:* `{daily_trend}`\n⏰ *Time:* `{now}` IST"
                send_telegram(msg)

            # Engine 2: 4H + 15M Logic
            if len(df_4h_res) >= 20:
                high_4h_20 = df_4h_res['High'].iloc[-20:].max()
                low_4h_20 = df_4h_res['Low'].iloc[-20:].min()
                eq_4h_50 = low_4h_20 + (high_4h_20 - low_4h_20) * 0.50

                is_4h_bull_fvg = df_4h_res['High'].iloc[-4] < df_4h_res['Low'].iloc[-2]
                is_4h_bear_fvg = df_4h_res['Low'].iloc[-4] > df_4h_res['High'].iloc[-2]
                high_4h_sweep = df_4h_res['High'].iloc[-1] > df_4h_res['High'].iloc[-5:-1].max()
                low_4h_sweep = df_4h_res['Low'].iloc[-1] < df_4h_res['Low'].iloc[-5:-1].min()

                curr_close_15m = df_15m['Close'].iloc[-1]
                recent_15m_high = df_15m['High'].iloc[-4:-1].max()
                recent_15m_low = df_15m['Low'].iloc[-4:-1].min()
                buffer_15m = 0.20 if "JPY" in pair else 0.00150

                if daily_trend == "BULLISH" and live_price < eq_4h_50 and (is_4h_bull_fvg or low_4h_sweep) and curr_close_15m > recent_15m_high:
                    sl_val = round(df_15m['Low'].iloc[-4:].min() - buffer_15m, 5)
                    tp_val = round(high_20, 5)
                    msg = f"🚀 *ENGINE 2: 4H SWING (BUY)*\n\n🔹 *Pair:* `{pair}`\n🟢 *Entry:* `{live_price}`\n🔴 *SL:* `{sl_val}`\n🎯 *TP:* `{tp_val}`\n🧭 *Trend:* `{daily_trend}`\n⏰ *Time:* `{now}` IST"
                    send_telegram(msg)

                elif daily_trend == "BEARISH" and live_price > eq_4h_50 and (is_4h_bear_fvg or high_4h_sweep) and curr_close_15m < recent_15m_low:
                    sl_val = round(df_15m['High'].iloc[-4:].max() + buffer_15m, 5)
                    tp_val = round(low_20, 5)
                    msg = f"🔻 *ENGINE 2: 4H SWING (SELL)*\n\n🔹 *Pair:* `{pair}`\n🟢 *Entry:* `{live_price}`\n🔴 *SL:* `{sl_val}`\n🎯 *TP:* `{tp_val}`\n🧭 *Trend:* `{daily_trend}`\n⏰ *Time:* `{now}` IST"
                    send_telegram(msg)

            time.sleep(1.2)
        except Exception as e:
            print(f"Error on {pair}: {e}")

    print("✅ Swing scan completed successfully.")

if __name__ == "__main__":
    scan_market()
