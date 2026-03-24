import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, filters,
    ContextTypes, CommandHandler
)
from groq import Groq
from pymongo import MongoClient
from datetime import datetime
import asyncio

# -----------------------
# CONFIG
# -----------------------
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

RENDER_URL = os.environ.get("RENDER_URL") # 🔥 change this

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

    user_message_lower = user_message.lower()

    # ✅ Custom replies
    if user_message_lower in ["hi", "hello", "hey"]:
        reply = "Hello 👋 How can I help you today?"
    elif user_message_lower in ["bye", "goodbye"]:
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

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi there! 😊 What would you like to know?")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    history.delete_many({"user_id": user_id})
    await update.message.reply_text("Your data has been cleared 🧹")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Go and ask devloper 😝")

async def hari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("He is GAY 💩")


# -----------------------
# ADD HANDLERS
# -----------------------
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("clear", clear))
telegram_app.add_handler(CommandHandler("help", help))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -----------------------
# WEBHOOK ROUTE
# -----------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok"

# -----------------------
# HOME ROUTE (for uptime)
# -----------------------
@app.route("/")
def home():
    return "Bot is running!"

# -----------------------
# START APP
# -----------------------
if __name__ == "__main__":
    asyncio.run(telegram_app.initialize())
    asyncio.run(telegram_app.bot.set_webhook(f"{RENDER_URL}/{BOT_TOKEN}"))

    app.run(host="0.0.0.0", port=10000)
