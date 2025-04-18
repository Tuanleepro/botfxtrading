# main.py - Sửa lỗi phản hồi 1 lần duy nhất, giữ toàn bộ chức năng
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
        print("🔥 Đã nhận /start từ:", update.effective_user.username, flush=True)
        await update.message.reply_text("🤖 Bot TradingView đã sẵn sàng rồi nè!")
    except Exception as e:
        print("❌ Lỗi khi xử lý /start:", e, flush=True)

application.add_handler(CommandHandler("start", start))

# Bắt lỗi
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"❌ Lỗi không xác định: {context.error}", flush=True)

application.add_error_handler(error_handler)

# Route ping
@app.route('/')
def index():
    return "✅ Bot is running with webhook + TradingView data!"

# Route webhook — giờ không cần gọi initialize nữa
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return 'ok'

# Gửi thủ công
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

# Gửi ảnh
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

# Auto scan
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
        time.sleep(900)

# Thiết lập webhook
def setup_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("✅ Đã thiết lập webhook thành công.", flush=True)
    else:
        print("❌ Lỗi thiết lập webhook:", response.text, flush=True)

# Hàm khởi chạy chính
async def run():
    setup_webhook()
    await application.initialize()  # ✅ Gọi duy nhất 1 lần ở đây
    threading.Thread(target=auto_scan_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# Gọi chạy
if __name__ == "__main__":
    asyncio.run(run())
