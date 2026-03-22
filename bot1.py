import os
import threading
for flask import Flask

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from groq import Groq
from pymongo import MongoClient
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

client = Groq(api_key=GROQ_API_KEY)

mongo = MongoClient(MONGO_URI)
db = mongo["ai_bot"]
history = db["history"]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_message = update.message.text

    history.insert_one({
        "user_id": user_id,
        "role": "user",
        "message": user_message,
        "time": datetime.now()
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        print(e)
        reply = "Error occurred"

    history.insert_one({
        "user_id": user_id,
        "role": "assistant",
        "message": reply,
        "time": datetime.now()
    })

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT",10000))
    flask_app.run(host="0.0.0.0",port=port)

threading.Thread(target=run_web).start()

print("Bot running...")
app.run_polling()
