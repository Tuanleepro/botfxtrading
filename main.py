# main.py - Gửi tín hiệu kèm ảnh biểu đồ từ signal_engine.py (webhook version)
from flask import Flask, request
import requests
import threading
import time
import signal_engine
import os
import asyncio

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === Cấu hình ===
BOT_TOKEN = "7331189117:AAFjEXI-8rsNH4QXbxZLgiHbbSlyIvCqP3s"
CHAT_ID = "576589496"
WEBHOOK_URL = f"https://botfxtrading.onrender.com/{BOT_TOKEN}"  # ⚠️ Nhớ đổi nếu domain khác

app = Flask(__name__)
last_signal_cache = []

# Route mặc định để UptimeRobot ping
@app.route('/')
def index():
    return "✅ Bot is running with webhook + TradingView data!"

# Route webhook để nhận update từ Telegram
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    asyncio.run(application.process_update(update))
    return 'ok'

# Gửi tín hiệu thủ công qua API
@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    if not data:
        return "No JSON payload", 400
    message = f"{data['side']} {data['symbol']}\nSL: {data['sl']}\nTP: {data['tp']}"
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(telegram_url, json={"chat_id": CHAT_ID, "text": message})
    print("📤 Gửi tín hiệu thủ công:", message, flush=True)
    return "Message sent!", 200

# Lệnh kiểm tra bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot TradingView đã sẵn sàng rồi nè!")

# Gửi tín hiệu kèm ảnh
def send_signal_with_chart(signal):
    msg = f"""📊 {signal['side']} {signal['symbol']} ({signal['tf']})
🎯 Entry: {signal['entry']}
🛡 SL: {signal['sl']}
🎁 TP: {signal['tp']}
📈 RR: {signal['rr']}"""
    try:
        with open(signal["chart"], "rb") as photo:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            files = {"photo": photo}
            data = {"chat_id": CHAT_ID, "caption": msg}
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                print("✅ Đã gửi tín hiệu kèm ảnh:", signal["symbol"], flush=True)
            else:
                print("⚠️ Gửi ảnh thất bại:", response.text, flush=True)
    except Exception as e:
        print("❌ Lỗi khi gửi ảnh biểu đồ:", e, flush=True)

# ✅ Bản sửa hoàn chỉnh: auto_scan_loop có flush + sleep 30s để test
def auto_scan_loop():
    global last_signal_cache
    while True:
        try:
            print("🔁 Bắt đầu vòng quét tín hiệu mới...", flush=True)
            signals = signal_engine.get_trade_signal()
            if signals:
                print(f"📈 Tổng tín hiệu quét được: {len(signals)}", flush=True)
                new_signals = [s for s in signals if s not in last_signal_cache]
                if new_signals:
                    last_signal_cache = signals
                    for signal in new_signals:
                        print(f"🚀 Gửi tín hiệu: {signal['side']} {signal['symbol']} ({signal['tf']})", flush=True)
                        send_signal_with_chart(signal)
                else:
                    print("⚠️ Không có tín hiệu mới (bị trùng).", flush=True)
            else:
                print("⏳ Chưa có tín hiệu TradingView phù hợp.", flush=True)
        except Exception as e:
            print("❌ Lỗi khi quét tín hiệu:", e, flush=True)
        time.sleep(30)  # 👉 test nhanh, sau đổi lại 900

# Khởi tạo bot app
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))

# Thiết lập webhook khi khởi động
def setup_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("✅ Đã thiết lập webhook thành công.", flush=True)
    else:
        print("❌ Lỗi thiết lập webhook:", response.text, flush=True)

# Khởi động Flask + auto_scan
if __name__ == "__main__":
    setup_webhook()
    threading.Thread(target=auto_scan_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
