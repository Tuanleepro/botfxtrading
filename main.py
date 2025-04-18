# main.py - Gửi tín hiệu kèm ảnh biểu đồ từ signal_engine.py
from flask import Flask, request
import requests
import threading
import time
import datetime
import signal_engine

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === Cấu hình ===
BOT_TOKEN = "7331189117:AAHYXCB5VhkG2Hrr4jySusQmnleQtzTfhl4"
CHAT_ID = "576589496"

app = Flask(__name__)
last_signal_cache = []

# Route kiểm tra bot online
@app.route('/')
def index():
    return "✅ Bot is running with TradingView data!"

# Gửi tín hiệu thủ công
@app.route('/send', methods=['POST'])
def send():
    data = request.get_json()
    if not data:
        return "No JSON payload", 400

    message = f"{data['side']} {data['symbol']}\nSL: {data['sl']}\nTP: {data['tp']}"
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(telegram_url, json={"chat_id": CHAT_ID, "text": message})
    print("📤 Gửi tín hiệu thủ công:", message)
    return "Message sent!", 200

# Lệnh kiểm tra bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot TradingView đã sẵn sàng rồi nè!")

# Gửi ảnh chart kèm tín hiệu
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
            requests.post(url, files=files, data=data)
            print("✅ Đã gửi tín hiệu:", signal["symbol"])
    except Exception as e:
        print("❌ Lỗi gửi ảnh:", e)

# Vòng lặp quét tín hiệu mỗi 15 phút, chỉ T2 → T6
def auto_scan_loop():
    global last_signal_cache
    while True:
        weekday = datetime.datetime.now().weekday()  # 0=Thứ 2, 6=Chủ nhật
        if weekday <= 4:  # Thứ 2 đến Thứ 6
            try:
                signals = signal_engine.get_trade_signal()
                if signals:
                    new_signals = [s for s in signals if s not in last_signal_cache]
                    if new_signals:
                        last_signal_cache = signals
                        for signal in new_signals:
                            send_signal_with_chart(signal)
                    else:
                        print("⚠️ Không có tín hiệu mới (bị trùng)")
                else:
                    print("⏳ Chưa có tín hiệu phù hợp.")
            except Exception as e:
                print("❌ Lỗi quét tín hiệu:", e)
        else:
            print("📆 Hôm nay là Thứ 7/CN, bot đang nghỉ.")

        time.sleep(900)  # 15 phút

# Khởi chạy
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()
    threading.Thread(target=auto_scan_loop, daemon=True).start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.run_polling()
