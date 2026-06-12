import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters,
    ContextTypes, CommandHandler
)
from groq import Groq
from pymongo import MongoClient
from datetime import datetime

# -----------------------
# GLOBAL EVENT LOOP (FIX)
# -----------------------
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# -----------------------
# CONFIG
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
RENDER_URL = os.getenv("RENDER_URL")

# -----------------------
# INIT
# -----------------------
client = Groq(api_key=GROQ_API_KEY)

mongo = MongoClient(MONGO_URI)
db = mongo["ai_bot"]
history = db["history"]

app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# -----------------------
# HANDLE MESSAGE
# -----------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_message = update.message.text

    history.insert_one({
        "user_id": user_id,
        "role": "user",
        "message": user_message,
        "time": datetime.now()
    })

    msg = user_message.lower()

    if msg in ["hi", "hello", "hey"]:
        reply = "Hello 👋 How can I help you today?"
    elif msg in ["bye", "goodbye"]:
        reply = "Goodbye 👋 Have a great day!"
    else:
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": user_message}]
            )
            reply = response.choices[0].message.content
        except Exception as e:
            print(e)
            reply = "⚠️ Error occurred"

    history.insert_one({
        "user_id": user_id,
        "role": "assistant",
        "message": reply,
        "time": datetime.now()
    })

    await update.message.reply_text(reply)

# -----------------------
# COMMANDS
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi there! 😊 What would you like to know?")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    history.delete_many({"user_id": user_id})
    await update.message.reply_text("Your data has been cleared 🧹 from our data base")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Go and ask developer 😝")

# -----------------------
# ADD HANDLERS
# -----------------------
telegram_app.add_handler(CommandHandler("start Mr.Ai", start Mr.Ai))
telegram_app.add_handler(CommandHandler("clear Mr.Ai", clear Mr.Ai))
telegram_app.add_handler(CommandHandler("help MrAi", help Mr.Ai))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -----------------------
# WEBHOOK
# -----------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)

    loop.run_until_complete(
        telegram_app.process_update(update)
    )

    return "ok"

# -----------------------
# HOME ROUTE
# -----------------------
@app.route("/")
def home():
    return "Bot is running ✅"

# -----------------------
# START
# -----------------------
if __name__ == "__main__":
    loop.run_until_complete(telegram_app.initialize())
    loop.run_until_complete(
        telegram_app.bot.set_webhook(f"{RENDER_URL}/{BOT_TOKEN}")
    )

    PORT = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=PORT)
