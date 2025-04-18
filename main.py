from flask import Flask, request
import requests
import threading
import time
import signal_engine
import os

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7331189117:AAFjEXI-8rsNH4QXbxZLgiHbbSlyIvCqP3s"
CHAT_ID = "576589496"

app = Flask(__name__)
last_signal_cache = []

# Bot command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("🔥 Đã nhận /start từ:", update.effective_user.username, flush=True)
        await update.message.reply_text("🤖 Bot TradingView đã sẵn sàng rồi nè!")
    except Exception as e:
        print("❌ Lỗi khi xử lý /start:", e, flush=True)

# Gửi tín hiệu có ảnh
def send_signal_with_chart(signal):
    msg = f"""📊 {signal['side']} {signal['symbol']} ({signal['tf']})
🎯 Entry: {signal['entry']}
🛡 SL: {signal['sl']}
🎁 TP: {signal['tp']}
📈 RR: {signal['rr']}"""
    try:
        with open(signal["chart"], "rb") as photo:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                files={"photo": photo},
                data={"chat_id": CHAT_ID, "caption": msg},
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Đã gửi tín hiệu kèm ảnh:", signal["symbol"], flush=True)
            else:
                print("⚠️ Gửi ảnh thất bại:", response.text, flush=True)
    except Exception as e:
        print("❌ Lỗi khi gửi ảnh biểu đồ:", e, flush=True)

# Quét tín hiệu định kỳ
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

# Route để gửi tín hiệu thủ công
@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    if not data:
        return "No JSON payload", 400
    message = f"{data['side']} {data['symbol']}\nSL: {data['sl']}\nTP: {data['tp']}"
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
        print("📤 Gửi tín hiệu thủ công:", message, flush=True)
    except Exception as e:
        print("❌ Gửi thủ công lỗi:", e, flush=True)
    return "Message sent!", 200

# Route để UptimeRobot ping
@app.route("/")
def index():
    return "✅ Bot is alive with polling and auto signal!"

# Khởi tạo bot và chạy polling
if __name__ == "__main__":
    threading.Thread(target=auto_scan_loop, daemon=True).start()
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.run_polling()
