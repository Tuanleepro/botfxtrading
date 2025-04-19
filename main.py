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

# ==== Hàm tính khối lượng lot ====
def calculate_lot_size(entry, sl, symbol, balance=10000, risk_percent=0.005):
    pip_value = 10  # USD/pip/lot (cho cặp như EURUSD, GBPUSD)
    pip = abs(entry - sl)
    if pip == 0:
        return 0.0
    lot = (balance * risk_percent) / (pip * pip_value)
    return round(lot, 2)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("🔥 Đã nhận /start từ:", update.effective_user.username, flush=True)
        await update.message.reply_text("🤖 Bot TradingView đã sẵn sàng rồi nè!")
    except Exception as e:
        print("❌ Lỗi khi xử lý /start:", e, flush=True)

# Gửi ảnh + thông điệp có pattern, candle_time, lot size
def send_signal_with_chart(signal):
    lot_size = calculate_lot_size(signal["entry"], signal["sl"], signal["symbol"])
    msg = f"""📊 {signal['side']} {signal['symbol']} ({signal['tf']})
📅 Time: {signal['candle_time']}
🕯 Pattern: {signal['pattern']}
🎯 Entry: {signal['entry']}
🛡 SL: {signal['sl']}
🎁 TP: {signal['tp']}
📈 RR: {signal['rr']}
📌 Lot size: {lot_size} lot (0.5% rủi ro / $10,000)"""
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

# Tự động quét tín hiệu mỗi 15 phút
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

# Route gửi thủ công
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

# Route ping cho UptimeRobot
@app.route("/")
def index():
    return "✅ Bot is alive with polling + auto signal!"

# Chạy bot Telegram + Flask server song song
if __name__ == "__main__":
    threading.Thread(target=auto_scan_loop, daemon=True).start()

    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    def run_bot():
        app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.run_polling()

    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
