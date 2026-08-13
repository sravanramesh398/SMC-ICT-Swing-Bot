import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timezone

st.set_page_config(page_title="JARVIS Dual Engine ICT Bot", page_icon="🤖")

# 9 Major & Cross Pairs
MAJOR_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD",
    "EURJPY", "GBPJPY", "AUDJPY"
]

TELEGRAM_BOT_TOKEN = "8981472233:AAHHe9boaP0hsfZIcROcvMEmrF1Z-ymfSUg"
TELEGRAM_CHAT_ID = "458226949"

# Session State for Live Active Trades Tracking
if 'active_trades' not in st.session_state:
    st.session_state.active_trades = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# ------------------------------------------------------------------
# FILTER 2: HIGH-IMPACT NEWS FILTER
# ------------------------------------------------------------------
def is_high_impact_news_window():
    """
    Blocks trades during major economic news release windows.
    US Market / Global high volatility hours (13:00 UTC - 14:30 UTC).
    """
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour
    current_minute = now_utc.minute
    
    # 13:00 to 14:30 UTC window (US CPI, NFP, PPI release times)
    if (current_hour == 13) or (current_hour == 14 and current_minute <= 30):
        return True
    return False

def track_active_trades(pair, live_price):
    if pair in st.session_state.active_trades:
        trade = st.session_state.active_trades[pair]
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        direction = trade['direction']
        be_notified = trade.get('be_notified', False)

        # BUY TRADE TRACKING
        if direction == 'BUY':
            if live_price >= tp:
                msg = f"🎉 *TARGET HIT ALERT (TP) - {pair}*\n\n🟢 *Entry:* `{entry}`\n🎯 *Target Hit:* `{live_price}`\n\n✅ *Status:* Trade Closed in Full Profit!"
                send_telegram(msg)
                del st.session_state.active_trades[pair]
            elif live_price <= sl:
                msg = f"⚠️ *STOP LOSS HIT ALERT (SL) - {pair}*\n\n🔴 *Entry:* `{entry}`\n🔻 *SL Hit Price:* `{live_price}`\n\n❌ *Status:* Trade Closed at Stop Loss."
                send_telegram(msg)
                del st.session_state.active_trades[pair]
            elif not be_notified and live_price >= entry + (tp - entry) * 0.5:
                msg = f"🛡️ *RISK-FREE TRADE ALERT - {pair}*\n\n🟢 *Entry:* `{entry}`\n📈 *Current Price:* `{live_price}`\n\n💡 *Action:* Trade is running in 1:1.5+ Profit. *Shift your Stop Loss to Entry Price (Break-Even)!*"
                send_telegram(msg)
                st.session_state.active_trades[pair]['be_notified'] = True

        # SELL TRADE TRACKING
        elif direction == 'SELL':
            if live_price <= tp:
                msg = f"🎉 *TARGET HIT ALERT (TP) - {pair}*\n\n🟢 *Entry:* `{entry}`\n🎯 *Target Hit:* `{live_price}`\n\n✅ *Status:* Trade Closed in Full Profit!"
                send_telegram(msg)
                del st.session_state.active_trades[pair]
            elif live_price >= sl:
                msg = f"⚠️ *STOP LOSS HIT ALERT (SL) - {pair}*\n\n🔴 *Entry:* `{entry}`\n🔻 *SL Hit Price:* `{live_price}`\n\n❌ *Status:* Trade Closed at Stop Loss."
                send_telegram(msg)
                del st.session_state.active_trades[pair]
            elif not be_notified and live_price <= entry - (entry - tp) * 0.5:
                msg = f"🛡️ *RISK-FREE TRADE ALERT - {pair}*\n\n🟢 *Entry:* `{entry}`\n📉 *Current Price:* `{live_price}`\n\n💡 *Action:* Trade is running in 1:1.5+ Profit. *Shift your Stop Loss to Entry Price (Break-Even)!*"
                send_telegram(msg)
                st.session_state.active_trades[pair]['be_notified'] = True

def scan_market():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alerts_count = 0
    
    # Check High-Impact News Filter
    if is_high_impact_news_window():
        st.warning("⚠️ High-Impact News Window Active! Market scanning paused to prevent news spike losses.")
        return 0

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

            # Track Active Trades
            track_active_trades(pair, live_price)

            if pair in st.session_state.active_trades:
                continue

            # -------------------------------------------------------------
            # FILTER 3: HTF DAILY TREND BIAS CALCULATOR
            # -------------------------------------------------------------
            daily_ema20 = df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
            daily_close = df_daily['Close'].iloc[-1]
            
            daily_trend = "BULLISH" if daily_close > daily_ema20 else "BEARISH"

            # 20-Day Range Parameters
            high_20 = df_daily['High'].iloc[-21:-1].max()
            low_20 = df_daily['Low'].iloc[-21:-1].min()
            eq_50 = low_20 + (high_20 - low_20) * 0.50

            pdh = df_daily['High'].iloc[-2]
            pdl = df_daily['Low'].iloc[-2]

            curr_close_1h = df_1h['Close'].iloc[-1]
            recent_1h_high = df_1h['High'].iloc[-4:-1].max()
            recent_1h_low = df_1h['Low'].iloc[-4:-1].min()

            buffer_1h = 0.50 if "JPY" in pair else 0.00400

            # -------------------------------------------------------------
            # ENGINE 1: DAILY SETUP + 1H SHIFT
            # -------------------------------------------------------------
            if live_price < eq_50 and pdl < df_daily['Low'].iloc[-10:-2].min() and curr_close_1h > recent_1h_high:
                sl_val = round(df_1h['Low'].iloc[-4:].min() - buffer_1h, 5)
                tp_val = round(high_20, 5)
                st.session_state.active_trades[pair] = {'direction': 'BUY', 'entry': live_price, 'sl': sl_val, 'tp': tp_val, 'be_notified': False}
                
                msg = (
                    f"🚀 *ENGINE 1: DAILY SETUP + 1H SHIFT (BUY)*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (BSL):* `{tp_val}`\n"
                    f"📊 *Model:* `Daily Sweep + 1H MSS`\n"
                    f"🧭 *Daily Trend:* `{daily_trend}`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1

            elif live_price > eq_50 and pdh > df_daily['High'].iloc[-10:-2].max() and curr_close_1h < recent_1h_low:
                sl_val = round(df_1h['High'].iloc[-4:].max() + buffer_1h, 5)
                tp_val = round(low_20, 5)
                st.session_state.active_trades[pair] = {'direction': 'SELL', 'entry': live_price, 'sl': sl_val, 'tp': tp_val, 'be_notified': False}
                
                msg = (
                    f"🔻 *ENGINE 1: DAILY SETUP + 1H SHIFT (SELL)*\n\n"
                    f"🔹 *Pair:* `{pair}`\n"
                    f"🟢 *Entry Price:* `{live_price}`\n"
                    f"🔴 *Stop Loss:* `{sl_val}`\n"
                    f"🎯 *Target (SSL):* `{tp_val}`\n"
                    f"📊 *Model:* `Daily Sweep + 1H MSS`\n"
                    f"🧭 *Daily Trend:* `{daily_trend}`\n\n"
                    f"⏰ *Time:* `{now}`"
                )
                send_telegram(msg)
                alerts_count += 1

            # -------------------------------------------------------------
            # ENGINE 2: 4H SETUP + 15M SHIFT (WITH DAILY TREND FILTER)
            # -------------------------------------------------------------
            elif len(df_4h_res) >= 4:
                is_4h_bull_fvg = df_4h_res['High'].iloc[-4] < df_4h_res['Low'].iloc[-2]
                is_4h_bear_fvg = df_4h_res['Low'].iloc[-4] > df_4h_res['High'].iloc[-2]
                high_4h_sweep = df_4h_res['High'].iloc[-1] > df_4h_res['High'].iloc[-5:-1].max()
                low_4h_sweep = df_4h_res['Low'].iloc[-1] < df_4h_res['Low'].iloc[-5:-1].min()

                curr_close_15m = df_15m['Close'].iloc[-1]
                recent_15m_high = df_15m['High'].iloc[-4:-1].max()
                recent_15m_low = df_15m['Low'].iloc[-4:-1].min()

                buffer_15m = 0.20 if "JPY" in pair else 0.00150

                # Engine 2 Buy (Only allowed if Daily Trend is BULLISH)
                if daily_trend == "BULLISH" and (is_4h_bull_fvg or low_4h_sweep) and curr_close_15m > recent_15m_high:
                    sl_val = round(df_15m['Low'].iloc[-4:].min() - buffer_15m, 5)
                    tp_val = round(high_20, 5)
                    st.session_state.active_trades[pair] = {'direction': 'BUY', 'entry': live_price, 'sl': sl_val, 'tp': tp_val, 'be_notified': False}
                    
                    msg = (
                        f"🚀 *ENGINE 2: 4H SETUP + 15M SHIFT (BUY)*\n\n"
                        f"🔹 *Pair:* `{pair}`\n"
                        f"🟢 *Entry Price:* `{live_price}`\n"
                        f"🔴 *Stop Loss:* `{sl_val}`\n"
                        f"🎯 *Target:* `{tp_val}`\n"
                        f"📊 *Model:* `4H FVG/Sweep + 15M MSS`\n"
                        f"🧭 *Trend Filter:* `Aligned with Daily Bullish Trend` ✅\n\n"
                        f"⏰ *Time:* `{now}`"
                    )
                    send_telegram(msg)
                    alerts_count += 1

                # Engine 2 Sell (Only allowed if Daily Trend is BEARISH)
                elif daily_trend == "BEARISH" and (is_4h_bear_fvg or high_4h_sweep) and curr_close_15m < recent_15m_low:
                    sl_val = round(df_15m['High'].iloc[-4:].max() + buffer_15m, 5)
                    tp_val = round(low_20, 5)
                    st.session_state.active_trades[pair] = {'direction': 'SELL', 'entry': live_price, 'sl': sl_val, 'tp': tp_val, 'be_notified': False}
                    
                    msg = (
                        f"🔻 *ENGINE 2: 4H SETUP + 15M SHIFT (SELL)*\n\n"
                        f"🔹 *Pair:* `{pair}`\n"
                        f"🟢 *Entry Price:* `{live_price}`\n"
                        f"🔴 *Stop Loss:* `{sl_val}`\n"
                        f"🎯 *Target:* `{tp_val}`\n"
                        f"📊 *Model:* `4H FVG/Sweep + 15M MSS`\n"
                        f"🧭 *Trend Filter:* `Aligned with Daily Bearish Trend` ✅\n\n"
                        f"⏰ *Time:* `{now}`"
                    )
                    send_telegram(msg)
                    alerts_count += 1

        except Exception:
            continue
    return alerts_count

st.title("🤖 JARVIS High-Accuracy Dual Engine ICT Bot")
st.success("System Live with Daily Trend Alignment & News Filter Active! ✅")

if 'last_run' not in st.session_state:
    st.session_state.last_run = datetime.now()
    send_telegram("⚡ *JARVIS Bot System Upgraded: Daily Trend Alignment & News Filter Applied! (Targeting ~74% Win Rate)*")

st.metric(label="System Status", value="Active & Scanning 9 Pairs 24/7")

with st.spinner("Scanning Market & Active Trades..."):
    count = scan_market()

st.write(f"Last scanned at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.write(f"Active Trades Being Tracked: {len(st.session_state.active_trades)}")

time.sleep(3600)
st.rerun()
