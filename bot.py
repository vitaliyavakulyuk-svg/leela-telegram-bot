import os
from threading import Thread

from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# TELEGRAM BOT TOKEN
# =========================

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


# =========================
# WEB SERVER FOR RENDER
# =========================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Leela Telegram Bot is running!"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


def keep_alive():
    thread = Thread(target=run_web_server)
    thread.daemon = True
    thread.start()


# =========================
# BOT MENU
# =========================

menu = ReplyKeyboardMarkup(
    [
        ["🎲 Кинути кубик"],
        ["🗺️ Поле гри", "🃏 Відкрити карту"],
        ["📍 Моя клітинка"],
    ],
    resize_keyboard=True,
)


# =========================
# /START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "✨ Вітаю у просторі гри «Ліла — гра життя»!\n\n"
        "Цей бот буде твоїм помічником під час нашої гри. "
        "Тут ти зможеш 🎲 кидати кубик, 🗺️ відкривати поле "
        "та 🃏 знаходити карту клітинки, на яку потрапляєш.\n\n"
        "Я буду поруч і проведу тебе через гру особисто.\n\n"
        "✨ Готова/готовий почати?",
        reply_markup=menu,
    )


# =========================
# DICE
# =========================

async def roll_dice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    dice_message = await update.message.reply_dice(
        emoji="🎲"
    )

    roll = dice_message.dice.value

    await update.message.reply_text(
        f"Твій результат: {roll} 🎲",
        reply_markup=menu,
    )


# =========================
# MENU BUTTONS
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text

    if text == "🎲 Кинути кубик":
        await roll_dice(update, context)

    elif text == "🗺️ Поле гри":
        await update.message.reply_text(
            "🗺️ Тут буде поле гри «Ліла».",
            reply_markup=menu,
        )

    elif text == "🃏 Відкрити карту":
        await update.message.reply_text(
            "🃏 Тут ми додамо карти для кожної клітинки.",
            reply_markup=menu,
        )

    elif text == "📍 Моя клітинка":
        await update.message.reply_text(
            "📍 Тут бот буде показувати твою поточну клітинку.",
            reply_markup=menu,
        )


# =========================
# START APPLICATION
# =========================

def main():
    print("Starting Leela bot...")

    # Start web server so Render detects an open port
    keep_alive()

    # Create Telegram application
    app = Application.builder().token(TOKEN).build()

    # Add handlers
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Leela bot is running!")

    # Start Telegram polling
    app.run_polling()


if __name__ == "__main__":
    main()
