import json
import os
import secrets
import zipfile
from pathlib import Path
from threading import Lock, Thread

from flask import Flask
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_PATH = BASE_DIR / "leela_bot_images.zip"
ASSETS_DIR = Path("/tmp/leela_bot_images")
BOARD_PATH = ASSETS_DIR / "board.jpg"
CARDS_DIR = ASSETS_DIR / "cards"
HISTORY_PATH = BASE_DIR / "leela_history.json"
WELCOME_PATH = BASE_DIR / "welcome.png"
HISTORY_LOCK = Lock()
SESSION_PATH = BASE_DIR / "leela_session.json"
SESSION_LOCK = Lock()
ADMIN_ID = 835856665

CARD_NAMES = {
    1: "Брама життя", 2: "Ілюзія", 3: "Гнів", 4: "Жадібність",
    5: "Матеріальний світ", 6: "Омана", 7: "Марнославство",
    8: "Ненаситність", 9: "Чуттєвий план", 10: "Очищення",
    11: "Розваги", 12: "Заздрість", 13: "Нікчемність", 14: "Насолода",
    15: "Уява", 16: "Ревнощі", 17: "Співчуття", 18: "Радість",
    19: "Карма", 20: "Чеснота", 21: "Каяття", 22: "Закони світобудови",
    23: "Сила", 24: "Погана компанія", 25: "Хороша компанія", 26: "Печаль",
    27: "Служіння", 28: "Віра", 29: "Відсутність віри",
    30: "Правильний шлях", 31: "Святість", 32: "Любов", 33: "Аромати",
    34: "Смак", 35: "Чистилище", 36: "Чистота", 37: "Мудрість",
    38: "Висхідний потік", 39: "Низхідний потік", 40: "План вогню",
    41: "Свобода", 42: "Вогонь", 43: "Нове Народження", 44: "Незнання",
    45: "Правильні знання", 46: "Розрізнення", 47: "Нейтральність",
    48: "Сонце", 49: "Місяць", 50: "Аскетизм", 51: "Земля",
    52: "Насилля", 53: "Вода", 54: "Духовна відданість", 55: "Егоїзм",
    56: "Вищі вібрації", 57: "Повітря", 58: "Сяйво", 59: "Реальність",
    60: "Правильне розуміння", 61: "Неправильне розуміння", 62: "Щастя",
    63: "Невігластво", 64: "Джерело творіння", 65: "Єдність",
    66: "Вища істина", 67: "Космічне благо", 68: "Космічна свідомість",
    69: "Абсолют", 70: "Спокій", 71: "Прийняття", 72: "Темрява",
}


def prepare_images():
    if not ARCHIVE_PATH.exists():
        raise FileNotFoundError(f"Image archive not found: {ARCHIVE_PATH}")
    if not BOARD_PATH.exists() or not (CARDS_DIR / "72.jpg").exists():
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ARCHIVE_PATH) as archive:
            archive.extractall(ASSETS_DIR)


def load_histories():
    if not HISTORY_PATH.exists():
        return {}
    try:
        with HISTORY_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


HISTORIES = load_histories()


def save_histories():
    temp_path = HISTORY_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(HISTORIES, file, ensure_ascii=False, indent=2)
    temp_path.replace(HISTORY_PATH)


def add_move(user_id, number):
    with HISTORY_LOCK:
        history = HISTORIES.setdefault(str(user_id), [])
        history.append(number)
        save_histories()
        return len(history)


def get_moves(user_id):
    with HISTORY_LOCK:
        return list(HISTORIES.get(str(user_id), []))


def clear_moves(user_id):
    with HISTORY_LOCK:
        HISTORIES[str(user_id)] = []
        save_histories()


def load_session():
    try:
        with SESSION_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict) and isinstance(data.get("allowed"), list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"open": False, "code": None, "allowed": [], "attempts": {}}


SESSION = load_session()


def save_session():
    temp_path = SESSION_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(SESSION, file, ensure_ascii=False)
    temp_path.replace(SESSION_PATH)


def has_access(user_id):
    with SESSION_LOCK:
        return bool(SESSION["open"] and
                    (user_id == ADMIN_ID or user_id in SESSION["allowed"]))


async def require_access(update, context):
    if has_access(update.effective_user.id):
        return True
    reset_prompt(context)
    with SESSION_LOCK:
        is_open = SESSION["open"]
    message = (
        "🔐 Гра відкрита. Введи код, який дала ведуча."
        if is_open else
        "🔐 Очікуй на код доступу від ведучої."
    )
    await update.message.reply_text(message, reply_markup=menu)
    return False


async def open_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or update.effective_chat.type != "private":
        await update.message.reply_text("Ця команда доступна лише ведучій у приватному чаті.")
        return
    with SESSION_LOCK:
        if SESSION["open"]:
            code = SESSION["code"]
            message = f"Гра вже відкрита. Код цієї сесії: {code}"
        else:
            code = f"{secrets.randbelow(90000000) + 10000000:08d}"
            SESSION.update(open=True, code=code, allowed=[], attempts={})
            save_session()
            message = f"🔓 Гру відкрито! Код для учасників: {code}\nПередай його лише гравцям за столом."
    await update.message.reply_text(message, reply_markup=menu)


async def close_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or update.effective_chat.type != "private":
        await update.message.reply_text("Ця команда доступна лише ведучій у приватному чаті.")
        return
    with SESSION_LOCK:
        SESSION.update(open=False, code=None, allowed=[], attempts={})
        save_session()
    await update.message.reply_text("🔒 Гру закрито. Кубик, поле та карти заблоковані; історія шляху доступна.", reply_markup=menu)


async def try_join(update, code):
    user_id = update.effective_user.id
    with SESSION_LOCK:
        if not SESSION["open"]:
            message = "🔒 Гра зараз не активна."
        elif user_id == ADMIN_ID or user_id in SESSION["allowed"]:
            message = "✅ Ти вже маєш доступ до цієї гри."
        else:
            attempts = SESSION["attempts"].get(str(user_id), 0)
            if attempts >= 5:
                message = "🔒 Забагато спроб. Попроси ведучу відкрити наступну сесію."
            elif secrets.compare_digest(code, str(SESSION["code"])):
                SESSION["allowed"].append(user_id)
                SESSION["attempts"].pop(str(user_id), None)
                save_session()
                message = "✅ Доступ відкрито! Можна грати."
            else:
                SESSION["attempts"][str(user_id)] = attempts + 1
                save_session()
                message = "Код не підійшов. Перевір його у ведучої."
    await update.message.reply_text(message, reply_markup=menu)


web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Leela Telegram Bot is running!"


def keep_alive():
    def run():
        web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), use_reloader=False)
    Thread(target=run, daemon=True).start()


menu = ReplyKeyboardMarkup([
    ["🎲 Кинути кубик"],
    ["🗺️ Поле гри", "🃏 Відкрити карту"],
    ["🧭 Мій шлях"],
    ["🗑️ Почати нову гру"],
], resize_keyboard=True)


def reset_prompt(context):
    for key in ("waiting_for_card", "waiting_for_clear"):
        context.user_data.pop(key, None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_prompt(context)
    welcome_text = (
        "✨ Вітаю у просторі гри «Ліла — гра життя»! ✨\n\n"
        "Це подорож до себе — через запитання, усвідомлення та підказки, "
        "які відкриватимуться на твоєму шляху.\n\n"
        "🔐 Перед початком ведуча відкриє гру й повідомить код доступу. "
        "Просто надішли цей код сюди одним повідомленням.\n\n"
        "🎲 Під час гри ти зможеш кидати кубик, переглядати поле й відкривати карти.\n"
        "🧭 У розділі «Мій шлях» збережеться історія всіх твоїх переходів.\n\n"
        "Налаштуйся на гру, сформулюй свій запит і дозволь собі бути чесною "
        "або чесним із собою 🤍"
    )
    if WELCOME_PATH.exists():
        with WELCOME_PATH.open("rb") as welcome:
            await update.message.reply_photo(
                welcome,
                caption=welcome_text,
                reply_markup=menu,
            )
    else:
        await update.message.reply_text(welcome_text, reply_markup=menu)


async def roll_dice(update, context):
    dice = await update.message.reply_dice(emoji="🎲")
    await update.message.reply_text(f"Твій результат: {dice.dice.value} 🎲", reply_markup=menu)


async def send_board(update):
    with BOARD_PATH.open("rb") as board:
        await update.message.reply_photo(board, caption="🗺️ Поле гри «Ліла» — клітинки 1–72", reply_markup=menu)


async def ask_for_card(update, context):
    reset_prompt(context)
    context.user_data["waiting_for_card"] = True
    await update.message.reply_text("🃏 Напиши номер карти від 1 до 72.", reply_markup=menu)


async def send_card(update, context, number):
    path = CARDS_DIR / f"{number:02d}.jpg"
    if not path.exists():
        await update.message.reply_text("Не знайшла цю карту. Спробуй ще раз.", reply_markup=menu)
        return
    move_number = add_move(update.effective_user.id, number)
    reset_prompt(context)
    with path.open("rb") as card:
        await update.message.reply_photo(
            card,
            caption=(
                f"🃏 Карта №{number} — {CARD_NAMES[number]}\n"
                f"✅ Записано як хід {move_number}"
            ),
            reply_markup=menu,
        )


async def send_history(update):
    moves = get_moves(update.effective_user.id)
    if not moves:
        await update.message.reply_text(
            "📍 У тебе ще немає записаних клітинок.\n"
            "Натисни «🃏 Відкрити карту» та введи номер клітинки.", reply_markup=menu)
        return
    lines = ["📍 Твій шлях у грі:"]
    lines += [f"{i}. {number} — {CARD_NAMES[number]}" for i, number in enumerate(moves, 1)]
    await update.message.reply_text("\n".join(lines), reply_markup=menu)


async def ask_to_clear(update, context):
    reset_prompt(context)
    context.user_data["waiting_for_clear"] = True
    await update.message.reply_text(
        "🗑️ Очистити всі записані ходи й почати нову гру?\n"
        "Напиши «Так» для підтвердження або «Ні» для скасування.", reply_markup=menu)


async def handle_clear(update, context, text):
    if text.casefold() in {"так", "yes", "да"}:
        clear_moves(update.effective_user.id)
        reset_prompt(context)
        await update.message.reply_text("✨ Історію очищено. Можна починати нову гру!", reply_markup=menu)
    elif text.casefold() in {"ні", "нi", "no", "нет"}:
        reset_prompt(context)
        await update.message.reply_text("Добре, твої ходи збережено.", reply_markup=menu)
    else:
        await update.message.reply_text("Будь ласка, напиши «Так» або «Ні».", reply_markup=menu)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Напиши боту в приватному чаті.")
        return
    text = update.message.text.strip()
    if text == "🧭 Мій шлях":
        reset_prompt(context)
        await send_history(update)
        return
    if text.isdigit() and len(text) == 8 and not has_access(update.effective_user.id):
        await try_join(update, text)
        return
    if not await require_access(update, context):
        return
    if text == "🎲 Кинути кубик":
        reset_prompt(context)
        await roll_dice(update, context)
    elif text == "🗺️ Поле гри":
        reset_prompt(context)
        await send_board(update)
    elif text == "🃏 Відкрити карту":
        await ask_for_card(update, context)
    elif text == "🗑️ Почати нову гру":
        await ask_to_clear(update, context)
    elif context.user_data.get("waiting_for_clear"):
        await handle_clear(update, context, text)
    elif context.user_data.get("waiting_for_card"):
        if text.isdigit() and 1 <= int(text) <= 72:
            await send_card(update, context, int(text))
        else:
            await update.message.reply_text("Будь ласка, введи число від 1 до 72.", reply_markup=menu)


def main():
    print("Starting Leela bot...")
    prepare_images()
    keep_alive()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open_game", open_game))
    app.add_handler(CommandHandler("close_game", close_game))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Leela bot is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
