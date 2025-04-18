# main.py - FINAL FIXED VERSION: Giữ nguyên chức năng, sửa lỗi event loop + phản hồi /start nhiều lần

from flask import Flask, request
import requests
import threading
import time
import signal_engine
import os
import asyncio

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7331189117:AAFjEXI-8rsNH4QXbxZLgiHbbSlyIvCqP3s"
CHAT_ID = "576589496"
WEBHOOK_URL = f"https://botfxtrading.onrender.com/{BOT_TOKEN}"

app = Flask(__name__)
last_signal_cache = []

application = ApplicationBuilder().token(BOT_TOKEN).build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("\ud83d\udd25 \u0110\u00e3 nh\u1eadn /start t\u1eeb:", update.effective_user.username, flush=True)
        await update.message.reply_text("\ud83e\udd16 Bot TradingView \u0111\u00e3 s\u1eb5n s\u00e0ng r\u1ed3i n\u00e8!")
    except Exception as e:
        print("\u274c L\u1ed7i khi x\u1eed l\u00fd /start:", e, flush=True)

application.add_handler(CommandHandler("start", start))

# B\u1eaft l\u1ed7i
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"\u274c L\u1ed7i kh\u00f4ng x\u00e1c \u0111\u1ecbnh: {context.error}", flush=True)

application.add_error_handler(error_handler)

# Route ping
@app.route('/')
def index():
    return "\u2705 Bot is running with webhook + TradingView data!"

# Route webhook
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    asyncio.create_task(application.process_update(update))
    return 'ok'

# G\u1eedi t\u1ee7 c\u00f4ng
@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    if not data:
        return "No JSON payload", 400
    message = f"{data['side']} {data['symbol']}\nSL: {data['sl']}\nTP: {data['tp']}"
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(telegram_url, json={"chat_id": CHAT_ID, "text": message})
    print("\ud83d\udce4 G\u1eedi t\u00edn hi\u1ec7u th\u1ee7 c\u00f4ng:", message, flush=True)
    return "Message sent!", 200

# G\u1eedi \u1ea3nh
def send_signal_with_chart(signal):
    msg = f"""\ud83d\udcca {signal['side']} {signal['symbol']} ({signal['tf']})
\ud83c\udfaf Entry: {signal['entry']}
\ud83d\udee1 SL: {signal['sl']}
\ud83c\udff1 TP: {signal['tp']}
\ud83d\udcc8 RR: {signal['rr']}"""
    try:
        with open(signal["chart"], "rb") as photo:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            files = {"photo": photo}
            data = {"chat_id": CHAT_ID, "caption": msg}
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                print("\u2705 \u0110\u00e3 g\u1eedi t\u00edn hi\u1ec7u k\u00e8m \u1ea3nh:", signal["symbol"], flush=True)
            else:
                print("\u26a0\ufe0f G\u1eedi \u1ea3nh th\u1ea5t b\u1ea1i:", response.text, flush=True)
    except Exception as e:
        print("\u274c L\u1ed7i khi g\u1eedi \u1ea3nh bi\u1ec3u \u0111\u1ed3:", e, flush=True)

# Auto scan
def auto_scan_loop():
    global last_signal_cache
    while True:
        try:
            print("\ud83d\udd01 B\u1eaft \u0111\u1ea7u v\u00f2ng qu\u00e9t t\u00edn hi\u1ec7u...", flush=True)
            signals = signal_engine.get_trade_signal()
            if signals:
                new_signals = [s for s in signals if s not in last_signal_cache]
                if new_signals:
                    last_signal_cache = signals
                    for signal in new_signals:
                        print(f"\ud83d\ude80 G\u1eedi t\u00edn hi\u1ec7u: {signal['side']} {signal['symbol']} ({signal['tf']})", flush=True)
                        send_signal_with_chart(signal)
                else:
                    print("\u26a0\ufe0f Kh\u00f4ng c\u00f3 t\u00edn hi\u1ec7u m\u1edbi.", flush=True)
            else:
                print("\u23f3 Ch\u01b0a c\u00f3 t\u00edn hi\u1ec7u TradingView ph\u00f9 h\u1ee3p.", flush=True)
        except Exception as e:
            print("\u274c L\u1ed7i khi qu\u00e9t t\u00edn hi\u1ec7u:", e, flush=True)
        time.sleep(900)

# Kh\u1edfi \u0111\u1ed9ng
async def run():
    setup_webhook()
    await application.initialize()
    threading.Thread(target=auto_scan_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# Thi\u1ebft l\u1eadp webhook
def setup_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("\u2705 \u0110\u00e3 thi\u1ebft l\u1eadp webhook", flush=True)
    else:
        print("\u274c L\u1ed7i thi\u1ebft l\u1eadp webhook:", response.text, flush=True)

if __name__ == "__main__":
    asyncio.run(run())
