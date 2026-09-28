import os
import zipfile
from pathlib import Path
from threading import Thread

from flask import Flask
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_PATH = BASE_DIR / "leela_bot_images.zip"
ASSETS_DIR = Path("/tmp/leela_bot_images")
BOARD_PATH = ASSETS_DIR / "board.jpg"
CARDS_DIR = ASSETS_DIR / "cards"


def prepare_images():
    if not ARCHIVE_PATH.exists():
        raise FileNotFoundError(f"Image archive not found: {ARCHIVE_PATH}")

    if not BOARD_PATH.exists() or not (CARDS_DIR / "72.jpg").exists():
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ARCHIVE_PATH) as archive:
            archive.extractall(ASSETS_DIR)


web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Leela Telegram Bot is running!"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)


def keep_alive():
    thread = Thread(target=run_web_server, daemon=True)
    thread.start()


menu = ReplyKeyboardMarkup(
    [
        ["🎲 Кинути кубик"],
        ["🗺️ Поле гри", "🃏 Відкрити карту"],
        ["📍 Моя клітинка"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_for_card", None)
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
    await update.message.reply_text(
        f"Твій результат: {dice_message.dice.value} 🎲",
        reply_markup=menu,
    )


async def send_board(update: Update):
    with BOARD_PATH.open("rb") as board:
        await update.message.reply_photo(
            photo=board,
            caption="🗺️ Поле гри «Ліла» — клітинки 1–72",
            reply_markup=menu,
        )


async def ask_for_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_for_card"] = True
    await update.message.reply_text(
        "🃏 Напиши номер карти від 1 до 72.",
        reply_markup=menu,
    )


async def send_card(update: Update, context: ContextTypes.DEFAULT_TYPE, number: int):
    card_path = CARDS_DIR / f"{number:02d}.jpg"
    if not card_path.exists():
        await update.message.reply_text(
            "Не знайшла цю карту. Спробуй ще раз.",
            reply_markup=menu,
        )
        return

    context.user_data.pop("waiting_for_card", None)
    with card_path.open("rb") as card:
        await update.message.reply_photo(
            photo=card,
            caption=f"🃏 Карта №{number}",
            reply_markup=menu,
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "🎲 Кинути кубик":
        context.user_data.pop("waiting_for_card", None)
        await roll_dice(update, context)
    elif text == "🗺️ Поле гри":
        context.user_data.pop("waiting_for_card", None)
        await send_board(update)
    elif text in {"🃏 Відкрити карту", "📍 Моя клітинка"}:
        await ask_for_card(update, context)
    elif context.user_data.get("waiting_for_card"):
        if text.isdigit() and 1 <= int(text) <= 72:
            await send_card(update, context, int(text))
        else:
            await update.message.reply_text(
                "Будь ласка, введи число від 1 до 72.",
                reply_markup=menu,
            )


def main():
    print("Starting Leela bot...")
    prepare_images()
    keep_alive()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Leela bot is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
