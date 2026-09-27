import os

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

menu = ReplyKeyboardMarkup(
    [
        ["🎲 Кинути кубик"],
        ["🗺️ Поле гри", "🃏 Відкрити карту"],
        ["📍 Моя клітинка"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Вітаю у просторі гри «Ліла — гра життя»!\n\n"
        "Цей бот буде твоїм помічником під час нашої гри. "
        "Тут ти зможеш 🎲 кидати кубик, 🗺️ відкривати поле "
        "та 🃏 знаходити карту клітинки, на яку потрапляєш.\n\n"
        "Я буду поруч і проведу тебе через гру особисто.\n\n"
        "✨ Готова/готовий почати?",
        reply_markup=menu,
    )


async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dice_message = await update.message.reply_dice(emoji="🎲")
    roll = dice_message.dice.value

    await update.message.reply_text(
        f"Твій результат: {roll} 🎲",
        reply_markup=menu,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def post_init(application: Application):
    await application.bot.get_me()


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Leela bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
