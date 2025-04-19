# signal_engine.py - Quét đa tín hiệu từ Twelve Data (Engulfing + Pinbar + Morning/Evening Star + Hình ảnh)
import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
import os

API_KEY = "f1f4a4b816d2443a85e3502aea2d4c61"
BASE_URL = "https://api.twelvedata.com/time_series"

symbols = ["EUR/USD", "GBP/USD", "USD/JPY"]

MIN_SL_DISTANCE = 0.0008
BUFFER = 0.0003

symbol_pip = {
    "USD/JPY": 0.01,
    "EUR/USD": 0.0001,
    "GBP/USD": 0.0001
}

def fetch_candles(symbol, interval="15min", outputsize=100):
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON"
    }
    res = requests.get(BASE_URL, params=params)
    data = res.json()

    if "values" not in data:
        print(f"⚠️ Lỗi dữ liệu {symbol}: {data}")
        return None

    df = pd.DataFrame(data["values"])
    df = df.iloc[::-1]
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df

def calculate_ema(df, span):
    return df["close"].ewm(span=span).mean()

def detect_bullish_engulfing(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    return (
        prev["close"] < prev["open"] and
        last["close"] > last["open"] and
        last["close"] > prev["open"] and
        last["open"] < prev["close"]
    )

def detect_bearish_engulfing(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    return (
        prev["close"] > prev["open"] and
        last["close"] < last["open"] and
        last["close"] < prev["open"] and
        last["open"] > prev["close"]
    )

def detect_bullish_pinbar(df):
    last = df.iloc[-1]
    body = abs(last["close"] - last["open"])
    full = last["high"] - last["low"]
    wick_bottom = min(last["close"], last["open"]) - last["low"]
    return (
        body < full * 0.3 and
        wick_bottom > body * 2 and
        last["close"] > last["open"]
    )

def detect_bearish_pinbar(df):
    last = df.iloc[-1]
    body = abs(last["close"] - last["open"])
    full = last["high"] - last["low"]
    wick_top = last["high"] - max(last["close"], last["open"])
    return (
        body < full * 0.3 and
        wick_top > body * 2 and
        last["close"] < last["open"]
    )

def detect_morning_star(df):
    if len(df) < 3: return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    return (
        a["close"] < a["open"] and
        abs(b["close"] - b["open"]) < (a["open"] - a["close"]) * 0.5 and
        c["close"] > c["open"] and
        c["close"] > ((a["open"] + a["close"]) / 2)
    )

def detect_evening_star(df):
    if len(df) < 3: return False
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    return (
        a["close"] > a["open"] and
        abs(b["close"] - b["open"]) < (a["close"] - a["open"]) * 0.5 and
        c["close"] < c["open"] and
        c["close"] < ((a["open"] + a["close"]) / 2)
    )

def find_swing_high(df):
    highs = df["high"].values
    for i in range(len(highs) - 3, 2, -1):
        if highs[i - 2] < highs[i - 1] < highs[i] > highs[i + 1] > highs[i + 2]:
            return highs[i]
    return None

def find_swing_low(df):
    lows = df["low"].values
    for i in range(len(lows) - 3, 2, -1):
        if lows[i - 2] > lows[i - 1] > lows[i] < lows[i + 1] < lows[i + 2]:
            return lows[i]
    return None

def draw_chart(df, symbol, entry, sl, tp, tf):
    plt.figure(figsize=(10, 4))
    plt.plot(df["datetime"], df["close"], label="Close", linewidth=1)
    plt.axhline(entry, color='blue', linestyle='--', label=f'Entry: {entry}')
    plt.axhline(sl, color='red', linestyle='--', label=f'SL: {sl}')
    plt.axhline(tp, color='green', linestyle='--', label=f'TP: {tp}')
    plt.title(f"{symbol} - {tf}")
    plt.legend()
    plt.tight_layout()

    folder = "charts"
    os.makedirs(folder, exist_ok=True)
    filepath = f"{folder}/{symbol.replace('/', '')}_{tf}.png"
    plt.savefig(filepath)
    plt.close()
    return filepath

def get_signal(symbol, tf_label, interval):
    df = fetch_candles(symbol, interval=interval)
    if df is None or len(df) < 50:
        return None

    df["ema20"] = calculate_ema(df, 20)
    df["ema50"] = calculate_ema(df, 50)
    last = df.iloc[-1]
    entry = last["close"]
    signal_type = None

    if detect_bullish_engulfing(df) and last["ema20"] > last["ema50"]:
        signal_type = "Bullish Engulfing"
        side = "Buy"
    elif detect_bullish_pinbar(df) and last["ema20"] > last["ema50"]:
        signal_type = "Bullish Pinbar"
        side = "Buy"
    elif detect_morning_star(df) and last["ema20"] > last["ema50"]:
        signal_type = "Morning Star"
        side = "Buy"
    elif detect_bearish_engulfing(df) and last["ema20"] < last["ema50"]:
        signal_type = "Bearish Engulfing"
        side = "Sell"
    elif detect_bearish_pinbar(df) and last["ema20"] < last["ema50"]:
        signal_type = "Bearish Pinbar"
        side = "Sell"
    elif detect_evening_star(df) and last["ema20"] < last["ema50"]:
        signal_type = "Evening Star"
        side = "Sell"
    else:
        return None

    candle_time = str(last["datetime"])
    if side == "Buy":
        sl = df.iloc[-5:]["low"].min() - BUFFER
        tp = find_swing_high(df)
        if not sl or not tp: return None
        rr = (tp - entry) / (entry - sl)
    else:
        sl = df.iloc[-5:]["high"].max() + BUFFER
        tp = find_swing_low(df)
        if not sl or not tp: return None
        rr = (entry - tp) / (sl - entry)

    if rr < 1.7: return None

    return {
        "symbol": symbol,
        "side": side,
        "rr": round(rr, 2),
        "entry": round(entry, 4),
        "sl": round(sl, 4),
        "tp": round(tp, 4),
        "tf": tf_label,
        "pattern": signal_type,
        "candle_time": candle_time,
        "chart": draw_chart(df, symbol, entry, sl, tp, tf_label)
    }

def get_trade_signal():
    results = []
    for symbol in symbols:
        for tf_label, interval in [("M15", "15min"), ("H1", "1h")]:
            signal = get_signal(symbol, tf_label, interval)
            if signal:
                results.append(signal)
    return results if results else None
