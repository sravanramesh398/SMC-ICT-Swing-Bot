import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime

st.set_page_config(page_title="JARVIS 24/7 ICT Swing Bot", page_icon="🤖")

MAJOR_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD"]
TELEGRAM_BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
TELEGRAM_CHAT_ID = "458226949"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def scan_market():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alerts_count = 0
    
    for pair in MAJOR_PAIRS:
        try:
            ticker = f"{pair}=X"
            df_daily = yf.Ticker(ticker).history(period="60d", interval="1d")
            df_1h = yf.Ticker(ticker).history(period="10d", interval="1h")
            
            if df_daily.empty or df_1h.empty:
                continue

            live_price = round(df_1h['Close'].iloc[-1], 5)
            prev_10_low = df_daily['Low'].iloc[-11:-1].min()
            prev_10_high = df_daily['High'].iloc[-11:-1].max()
            
            yesterday_low = df_daily['Low'].iloc[-2]
            yesterday_high = df_daily['High'].iloc[-2]

            target_bsl = round(df_daily['High'].iloc[-15:-1].max(), 5)
            target_ssl = round(df_daily['Low'].iloc[-15:-1].min(), 5)
            
            curr_close = df_1h['Close'].iloc[-1]
            buffer = 0.50 if "JPY" in pair else 0.00400

            # Bullish ICT Swing Setup
            if yesterday_low < prev_10_low and curr_close > df_1h['High'].iloc[-2]:
                sl_val = round(min(yesterday_low, df_1h['Low'].iloc[-5:].min()) - buffer, 5)
                msg = (
                    f"🚀 *AUTOMATED ICT SWING BUY ALERT*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (BSL):* `{target_bsl}`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1

            # Bearish ICT Swing Setup
            elif yesterday_high > prev_10_high and curr_close < df_1h['Low'].iloc[-2]:
                sl_val = round(max(yesterday_high, df_1h['High'].iloc[-5:].max()) + buffer, 5)
                msg = (
                    f"🔻 *AUTOMATED ICT SWING SELL ALERT*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (SSL):* `{target_ssl}`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1
        except Exception:
            continue
    return alerts_count

st.title("🤖 JARVIS 24/7 Automated Swing Bot Engine")
st.success("Bot is Live on Streamlit Cloud Servers! ✅")

if 'last_run' not in st.session_state:
    st.session_state.last_run = datetime.now()
    send_telegram("🚀 *JARVIS 24/7 Cloud Bot Deployed Successfully! Running live on Cloud.*")

st.metric(label="Status", value="Active & Scanning 24/7")

with st.spinner("Scanning Market..."):
    count = scan_market()

st.write(f"Last scanned at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write(f"Alerts dispatched in this cycle: {count}")

# Auto refresh every 1 hour (3600 seconds)
time.sleep(3600)
st.rerun()
