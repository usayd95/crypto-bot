"""
Модуль генерации контента для X (Twitter)
==========================================
Генерирует готовые тексты постов и тредов для X на основе крипто-новостей.
Ты просто копируешь текст и публикуешь сам.

Команды:
    /x_post       — сгенерировать пост для X
    /x_thread     — сгенерировать тред (цепочку твитов)
    /x_reply @url — подготовить текст комментария под конкретный пост
    /x_ideas      — 5 идей для постов на сегодня
"""

import os
import logging
import google.generativeai as genai

log = logging.getLogger(__name__)

GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@ваш_канал")


def get_gemini():
    """Инициализирует и возвращает модель Gemini."""
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.0-flash")  # или gemini-1.5-flash


# ─── ГЕНЕРАТОРЫ ──────────────────────────────────────────────────────────────

def gen_x_post(topic: str = "") -> str:
    """Сгенерировать одиночный пост для X (до 280 символов)."""
    model = get_gemini()
    prompt = f"""Ты крипто-эксперт с популярным аккаунтом на X (Twitter).
Напиши 1 пост на русском языке {'на тему: ' + topic if topic else 'на актуальную крипто-тему'}.

Требования:
- Максимум 260 символов (оставь место для ссылки)
- Цепляющее начало — первые 2-3 слова должны останавливать скролл
- Конкретная мысль или факт, а не общие слова
- В конце добавь: 👉 {CHANNEL_ID}
- 1-2 хэштега максимум
- Без эмодзи-спама, только 1-2 уместных

Верни только текст поста."""

    response = model.generate_content(prompt)
    return response.text.strip()


def gen_x_thread(topic: str = "") -> list[str]:
    """Сгенерировать тред из 5 твитов для X."""
    model = get_gemini()
    prompt = f"""Ты крипто-эксперт на X (Twitter).
Напиши тред из 5 твитов на русском {'на тему: ' + topic if topic else 'на актуальную крипто-тему'}.

Формат ответа — строго 5 пунктов, каждый с новой строки, пронумерованных:
1. [текст первого твита — цепляющий вопрос или факт, до 260 символов]
2. [текст второго твита — развитие темы, до 260 символов]
3. [текст третьего твита — ключевой инсайт, до 260 символов]
4. [текст четвёртого твита — практический вывод, до 260 символов]
5. [текст пятого твита — призыв к действию + ссылка на канал {CHANNEL_ID}, до 260 символов]

Правила:
- Каждый твит самодостаточен, но вместе они рассказывают историю
- Конкретные цифры и факты, не общие слова
- Живой разговорный стиль
- Верни только 5 пронумерованных твитов, без пояснений."""

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Парсим пронумерованный список
    tweets = []
    for line in text.split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and ". " in line:
            tweets.append(line.split(". ", 1)[1].strip())
    return tweets if tweets else [text]


def gen_x_reply(post_text: str) -> str:
    """Сгенерировать текст комментария под конкретный пост."""
    model = get_gemini()
    prompt = f"""Ты крипто-эксперт на X (Twitter).
Под этим постом нужно оставить вдумчивый комментарий:

«{post_text}»

Требования:
- До 240 символов
- Добавь что-то ценное к теме (факт, уточнение, противоположная точка зрения)
- Не лесть, а реальная мысль
- В конце ненавязчиво: "Разбираем подробнее в {CHANNEL_ID}"
- Русский язык

Верни только текст комментария."""

    response = model.generate_content(prompt)
    return response.text.strip()


def gen_x_ideas() -> list[str]:
    """Сгенерировать 5 идей для постов на сегодня."""
    model = get_gemini()
    prompt = """Ты контент-стратег для крипто-аккаунта на X (Twitter).
Дай 5 конкретных идей для постов на сегодня на русском языке.

Формат — 5 строк, каждая начинается с эмодзи и содержит:
- Тему поста
- Почему это актуально сейчас
- Формат (пост / тред / опрос / мнение)

Верни только 5 идей, без вступления."""

    response = model.generate_content(prompt)
    return [line.strip() for line in response.text.strip().split("\n") if line.strip()]


# ─── КОМАНДЫ БОТА ────────────────────────────────────────────────────────────

from telegram.ext import CommandHandler, ContextTypes


async def cmd_x_post(update, context: ContextTypes.DEFAULT_TYPE):
    """/x_post [тема] — сгенерировать пост для X."""
    topic = " ".join(context.args) if context.args else ""
    await update.message.reply_text("⏳ Генерирую пост для X...")
    try:
        post = gen_x_post(topic)
        chars = len(post)
        await update.message.reply_text(
            f"📝 Готовый пост для X ({chars} символов):\n\n"
            f"<code>{post}</code>\n\n"
            "👆 Скопируй и опубликуй на своём аккаунте X.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_x_thread(update, context: ContextTypes.DEFAULT_TYPE):
    """/x_thread [тема] — сгенерировать тред для X."""
    topic = " ".join(context.args) if context.args else ""
    await update.message.reply_text("⏳ Генерирую тред...")
    try:
        tweets = gen_x_thread(topic)
        result = "🧵 Готовый тред для X:\n\n"
        for i, tweet in enumerate(tweets, 1):
            result += f"<b>{i}/{len(tweets)}</b>\n<code>{tweet}</code>\n\n"
        result += "👆 Публикуй по одному твиту в виде цепочки."
        await update.message.reply_text(result, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_x_reply(update, context: ContextTypes.DEFAULT_TYPE):
    """/x_reply текст поста — подготовить комментарий."""
    if not context.args:
        await update.message.reply_text(
            "Использование: /x_reply текст поста на который хочешь ответить\n"
            "Пример: /x_reply Bitcoin достиг нового ATH сегодня"
        )
        return
    post_text = " ".join(context.args)
    await update.message.reply_text("⏳ Готовлю комментарий...")
    try:
        reply = gen_x_reply(post_text)
        chars = len(reply)
        await update.message.reply_text(
            f"💬 Готовый комментарий ({chars} символов):\n\n"
            f"<code>{reply}</code>\n\n"
            "👆 Скопируй и оставь комментарий вручную.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def cmd_x_ideas(update, context: ContextTypes.DEFAULT_TYPE):
    """/x_ideas — 5 идей для постов на сегодня."""
    await update.message.reply_text("⏳ Генерирую идеи...")
    try:
        ideas = gen_x_ideas()
        result = "💡 Идеи для постов на X сегодня:\n\n"
        result += "\n\n".join(ideas)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ─── РЕГИСТРАЦИЯ ─────────────────────────────────────────────────────────────

def register_x_handlers(app):
    """Подключить команды X к боту."""
    app.add_handler(CommandHandler("x_post", cmd_x_post))
    app.add_handler(CommandHandler("x_thread", cmd_x_thread))
    app.add_handler(CommandHandler("x_reply", cmd_x_reply))
    app.add_handler(CommandHandler("x_ideas", cmd_x_ideas))
    log.info("Модуль X (Twitter) подключён.")
