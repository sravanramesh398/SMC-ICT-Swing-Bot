import os
import datetime
import pytz
import requests
import pandas as pd
import numpy as np

# ==========================================================
# ⚙️ 1. കോൺഫിഗറേഷൻ & എൻവയോൺമെന്റ് വേരിയബിളുകൾ
# ==========================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "demo") # സൗജന്യ API കീ ഇവിടെ നൽകാം

SYMBOLS = ["EUR/USD", "GBP/USD", "USD/CHF"]
RR_RATIO = 3.0
BUFFER_PIPS = 1.0

# ==========================================================
# 📲 2. ടെലിഗ്രാം അലേർട്ട് ഫംഗ്ഷൻ
# ==========================================================
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==========================================================
# 🛑 3. ന്യൂസ് ഫിൽട്ടർ (NEWS BLACKOUT)
# ==========================================================
def is_news_blackout(time_val_est):
    if 8.30 <= time_val_est <= 9.17 or 10.0 <= time_val_est <= 10.67:
        return True
    return False

# ==========================================================
# ⏰ 4. കിൽസോൺ പരിശോധന (IST BASED)
# ==========================================================
def get_current_killzone(ist_time):
    time_val = ist_time.hour + ist_time.minute / 60.0
    if 12.50 <= time_val <= 15.50:
        return True, "London Killzone"
    elif 17.50 <= time_val <= 20.50:
        return True, "New York Killzone"
    return False, "Outside Killzone"

# ==========================================================
# 📊 5. TWELVE DATA API വഴി ഡാറ്റ ശേഖരണം
# ==========================================================
def get_forex_data(symbol, interval, outputsize=100):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if "values" not in data:
            return None
        df = pd.DataFrame(data["values"])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df = df.astype(float)
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        print(f"API Error for {symbol}: {e}")
        return None

# ==========================================================
# 🔍 6. PURE ICT 4H STRUCTURE & PvD CALCULATION
# ==========================================================
def get_ict_4h_bias_and_pvd(symbol):
    df_4h = get_forex_data(symbol, "4h", 60)
    if df_4h is None or len(df_4h) < 25:
        return 0, 0.0
        
    highs = df_4h['high'].values
    lows = df_4h['low'].values
    closes = df_4h['close'].values
    n = len(df_4h)
    lookback = 2
    
    swing_highs = []
    swing_lows = []
    for i in range(lookback, n - lookback):
        if all(highs[i] > highs[i - j] for j in range(1, lookback + 1)) and all(highs[i] > highs[i + j] for j in range(1, lookback + 1)):
            swing_highs.append((i, highs[i]))
        if all(lows[i] < lows[i - j] for j in range(1, lookback + 1)) and all(lows[i] < lows[i + j] for j in range(1, lookback + 1)):
            swing_lows.append((i, lows[i]))
            
    curr_bias = 0
    sh_idx = 0
    sl_idx = 0
    recent_sh = np.nan
    recent_sl = np.nan
    
    for i in range(n):
        while sh_idx < len(swing_highs) and swing_highs[sh_idx][0] + lookback <= i:
            recent_sh = swing_highs[sh_idx][1]
            sh_idx += 1
        while sl_idx < len(swing_lows) and swing_lows[sl_idx][0] + lookback <= i:
            recent_sl = swing_lows[sl_idx][1]
            sl_idx += 1
            
        if not np.isnan(recent_sh) and closes[i] > recent_sh:
            curr_bias = 1
        elif not np.isnan(recent_sl) and closes[i] < recent_sl:
            curr_bias = -1
            
    range_high = df_4h['high'].iloc[-20:].max()
    range_low = df_4h['low'].iloc[-20:].min()
    equilibrium = (range_high + range_low) / 2.0
    
    return curr_bias, equilibrium

# ==========================================================
# 🤖 7. MAIN BOT LOGIC
# ==========================================================
def run_bot():
    utc_now = datetime.datetime.now(pytz.utc)
    ist_now = utc_now.astimezone(pytz.timezone('Asia/Kolkata'))
    est_now = utc_now.astimezone(pytz.timezone('US/Eastern'))
    today_date = ist_now.date()

    in_kz, kz_name = get_current_killzone(ist_now)
    if not in_kz or is_news_blackout(est_now.hour + est_now.minute / 60.0):
        print("Outside Killzone or News Blackout. Skipping...")
        return

    for symbol in SYMBOLS:
        htf_bias, equilibrium = get_ict_4h_bias_and_pvd(symbol)
        if htf_bias == 0:
            continue

        df_d1 = get_forex_data(symbol, "1day", 5)
        if df_d1 is None or len(df_d1) < 2:
            continue
        pdh = df_d1['high'].iloc[-2]
        pdl = df_d1['low'].iloc[-2]

        df_3m = get_forex_data(symbol, "5min", 50) # 5min API interval (closest to 3m free tier)
        if df_3m is None or len(df_3m) < 10:
            continue

        curr_bar = df_3m.iloc[-1]
        recent_swing_high = df_3m['high'].iloc[-7:-2].max()
        recent_swing_low = df_3m['low'].iloc[-7:-2].min()

        day_bars = df_3m[df_3m.index.date == today_date]
        asian_bars = day_bars[(day_bars.index.hour + day_bars.index.minute/60.0 >= 5.5) & 
                              (day_bars.index.hour + day_bars.index.minute/60.0 < 11.5)]
        
        asian_high = asian_bars['high'].max() if len(asian_bars) > 0 else pdh
        asian_low = asian_bars['low'].min() if len(asian_bars) > 0 else pdl

        high_swept = df_3m['high'].iloc[-10:].max() > max(pdh, asian_high)
        low_swept = df_3m['low'].iloc[-10:].min() < min(pdl, asian_low)
        sweep_high_price = df_3m['high'].iloc[-10:].max()
        sweep_low_price = df_3m['low'].iloc[-10:].min()

        buffer = BUFFER_PIPS * 0.0001
        max_sl_pips = 0.0040

        # 🟢 BUY SETUP
        if htf_bias == 1 and low_swept and (curr_bar['close'] < equilibrium) and (curr_bar['close'] > recent_swing_high):
            entry = curr_bar['close']
            sl = sweep_low_price - buffer
            risk = entry - sl

            if 0.0003 <= risk <= max_sl_pips:
                tp = entry + (risk * RR_RATIO)
                msg = (
                    f"🟢 *ICT SMC BUY SIGNAL* 🟢\n\n"
                    f"🔹 *Pair:* `{symbol}`\n"
                    f"🔹 *Session:* `{kz_name}`\n"
                    f"🔹 *4H Bias:* `BULLISH (BOS)`\n"
                    f"🔹 *Valuation:* `Discount Zone (< EQ)`\n\n"
                    f"📍 *Entry:* `{entry:.5f}`\n"
                    f"🛑 *Stop Loss:* `{sl:.5f}` ({risk*10000:.1f} Pips)\n"
                    f"🎯 *Take Profit (1:3):* `{tp:.5f}`\n\n"
                    f"⏰ *Time:* {ist_now.strftime('%I:%M %p IST')}"
                )
                send_telegram_alert(msg)
                break

        # 🔴 SELL SETUP
        elif htf_bias == -1 and high_swept and (curr_bar['close'] > equilibrium) and (curr_bar['close'] < recent_swing_low):
            entry = curr_bar['close']
            sl = sweep_high_price + buffer
            risk = sl - entry

            if 0.0003 <= risk <= max_sl_pips:
                tp = entry - (risk * RR_RATIO)
                msg = (
                    f"🔴 *ICT SMC SELL SIGNAL* 🔴\n\n"
                    f"🔹 *Pair:* `{symbol}`\n"
                    f"🔹 *Session:* `{kz_name}`\n"
                    f"🔹 *4H Bias:* `BEARISH (BOS)`\n"
                    f"🔹 *Valuation:* `Premium Zone (> EQ)`\n\n"
                    f"📍 *Entry:* `{entry:.5f}`\n"
                    f"🛑 *Stop Loss:* `{sl:.5f}` ({risk*10000:.1f} Pips)\n"
                    f"🎯 *Take Profit (1:3):* `{tp:.5f}`\n\n"
                    f"⏰ *Time:* {ist_now.strftime('%I:%M %p IST')}"
                )
                send_telegram_alert(msg)
                break

if __name__ == "__main__":
    run_bot()
