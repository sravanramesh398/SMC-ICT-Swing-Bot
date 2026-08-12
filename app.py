import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(page_title="JARVIS Dual Engine ICT Swing Bot", page_icon="🤖")

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
            df_15m = yf.Ticker(ticker).history(period="5d", interval="15m")
            
            if df_daily.empty or df_1h.empty or df_15m.empty or len(df_daily) < 20:
                continue

            # Resample 1H data to 4H
            df_4h_res = df_1h.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'
            }).dropna()

            live_price = round(df_15m['Close'].iloc[-1], 5)

            # -------------------------------------------------------------
            # ENGINE 1: DAILY SETUP + 1H SHIFT (Macro Swing Engine)
            # -------------------------------------------------------------
            high_20 = df_daily['High'].iloc[-21:-1].max()
            low_20 = df_daily['Low'].iloc[-21:-1].min()
            eq_50 = low_20 + (high_20 - low_20) * 0.50

            pdh = df_daily['High'].iloc[-2]
            pdl = df_daily['Low'].iloc[-2]

            curr_close_1h = df_1h['Close'].iloc[-1]
            recent_1h_high = df_1h['High'].iloc[-4:-1].max()
            recent_1h_low = df_1h['Low'].iloc[-4:-1].min()

            buffer_1h = 0.50 if "JPY" in pair else 0.00400

            # Daily Buy + 1H Shift
            if live_price < eq_50 and pdl < df_daily['Low'].iloc[-10:-2].min() and curr_close_1h > recent_1h_high:
                sl_val = round(df_1h['Low'].iloc[-4:].min() - buffer_1h, 5)
                msg = (
                    f"🚀 *ENGINE 1: DAILY SETUP + 1H SHIFT (BUY)*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (BSL):* `{round(high_20, 5)}`\n"
                    f"📊 *Model:* `Daily Liquidity Sweep + 1H MSS Confirmation`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1

            # Daily Sell + 1H Shift
            elif live_price > eq_50 and pdh > df_daily['High'].iloc[-10:-2].max() and curr_close_1h < recent_1h_low:
                sl_val = round(df_1h['High'].iloc[-4:].max() + buffer_1h, 5)
                msg = (
                    f"🔻 *ENGINE 1: DAILY SETUP + 1H SHIFT (SELL)*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (SSL):* `{round(low_20, 5)}`\n"
                    f"📊 *Model:* `Daily Liquidity Sweep + 1H MSS Confirmation`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1

            # -------------------------------------------------------------
            # ENGINE 2: 4H SETUP + 15M SHIFT (Intra-Swing Engine)
            # -------------------------------------------------------------
            if len(df_4h_res) >= 4:
                is_4h_bull_fvg = df_4h_res['High'].iloc[-4] < df_4h_res['Low'].iloc[-2]
                is_4h_bear_fvg = df_4h_res['Low'].iloc[-4] > df_4h_res['High'].iloc[-2]
                high_4h_sweep = df_4h_res['High'].iloc[-1] > df_4h_res['High'].iloc[-5:-1].max()
                low_4h_sweep = df_4h_res['Low'].iloc[-1] < df_4h_res['Low'].iloc[-5:-1].min()

                curr_close_15m = df_15m['Close'].iloc[-1]
                recent_15m_high = df_15m['High'].iloc[-4:-1].max()
                recent_15m_low = df_15m['Low'].iloc[-4:-1].min()

                buffer_15m = 0.20 if "JPY" in pair else 0.00150

                # 4H Buy + 15M Shift
                if (is_4h_bull_fvg or low_4h_sweep) and curr_close_15m > recent_15m_high:
                    sl_val = round(df_15m['Low'].iloc[-4:].min() - buffer_15m, 5)
                    msg = (
                        f"🚀 *ENGINE 2: 4H SETUP + 15M SHIFT (BUY)*\n\n"
                        f"🔹 *Pair:* `{pair}`\n"
                        f"🟢 *Entry Price:* `{live_price}`\n"
                        f"🔴 *Stop Loss:* `{sl_val}`\n"
                        f"🎯 *Target:* `{round(high_20, 5)}`\n"
                        f"📊 *Model:* `4H FVG/Sweep + 15M High R:R MSS Shift`\n\n"
                        f"⏰ *Time:* `{now}`"
                    )
                    send_telegram(msg)
                    alerts_count += 1

                # 4H Sell + 15M Shift
                elif (is_4h_bear_fvg or high_4h_sweep) and curr_close_15m < recent_15m_low:
                    sl_val = round(df_15m['High'].iloc[-4:].max() + buffer_15m, 5)
                    msg = (
                        f"🔻 *ENGINE 2: 4H SETUP + 15M SHIFT (SELL)*\n\n"
                        f"🔹 *Pair:* `{pair}`\n"
                        f"🟢 *Entry Price:* `{live_price}`\n"
                        f"🔴 *Stop Loss:* `{sl_val}`\n"
                        f"🎯 *Target:* `{round(low_20, 5)}`\n"
                        f"📊 *Model:* `4H FVG/Sweep + 15M High R:R MSS Shift`\n\n"
                        f"⏰ *Time:* `{now}`"
                    )
                    send_telegram(msg)
                    alerts_count += 1

        except Exception:
            continue
    return alerts_count

st.title("🤖 JARVIS 24/7 Dual Engine ICT Bot")
st.success("Engine 1 (Daily+1H) & Engine 2 (4H+15M) Both Active! ✅")

if 'last_run' not in st.session_state:
    st.session_state.last_run = datetime.now()
    send_telegram("🚀 *JARVIS Dual Engine Bot Active: Engine 1 (Daily+1H) & Engine 2 (4H+15M)*")

st.metric(label="System Status", value="Active & Scanning 24/7")

with st.spinner("Scanning Market..."):
    count = scan_market()

st.write(f"Last scanned at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write(f"Alerts dispatched in this cycle: {count}")

time.sleep(3600)
st.rerun()
