"""
Telegram Crypto Channel Bot
============================
Установка:
    pip install python-telegram-bot apscheduler requests anthropic

Файлы проекта:
    crypto_bot.py   — основной бот
    promo_helper.py — модуль взаимопиара

Настройка переменных окружения (Railway → Variables):
    TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather
    CHANNEL_ID=@твой_канал
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CRYPTOPANIC_API_KEY  (опционально)
"""

import os
import logging
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import anthropic
from promo_helper import register_promo_handlers
from x_helper import register_x_handlers

# ─── НАСТРОЙКИ ───────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID          = os.getenv("CHANNEL_ID", "@ваш_канал")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "ВАШ_КЛЮЧ")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

# Расписание — меняй как хочешь:
SCHEDULE = [
    {"hour": 9,  "minute": 0},
    {"hour": 13, "minute": 0},
    {"hour": 18, "minute": 0},
    {"hour": 21, "minute": 0},
]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ─── ПАРСИНГ НОВОСТЕЙ ─────────────────────────────────────────────────────────

def fetch_news_cryptopanic():
    try:
        resp = requests.get("https://cryptopanic.com/api/v1/posts/", params={
            "auth_token": CRYPTOPANIC_API_KEY,
            "public": "true", "kind": "news", "filter": "hot",
        }, timeout=10)
        return [{"title": r["title"], "url": r["url"]} for r in resp.json().get("results", [])[:5]]
    except Exception as e:
        log.warning(f"CryptoPanic: {e}")
        return []

def fetch_news_rss():
    try:
        import xml.etree.ElementTree as ET
        resp = requests.get("https://www.coindesk.com/arc/outboundfeeds/rss/", timeout=10)
        root = ET.fromstring(resp.content)
        return [
            {"title": i.findtext("title", "").strip(), "url": i.findtext("link", "").strip()}
            for i in root.findall(".//item")[:5]
            if i.findtext("title") and i.findtext("link")
        ]
    except Exception as e:
        log.warning(f"RSS: {e}")
        return []

def get_news():
    return (fetch_news_cryptopanic() if CRYPTOPANIC_API_KEY else []) or fetch_news_rss()

# ─── AI ОБРАБОТКА ─────────────────────────────────────────────────────────────

def ai_process_news(news_items):
    if not news_items:
        return None
    headlines = "\n".join(f"{i+1}. {n['title']} ({n['url']})" for i, n in enumerate(news_items))
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""Ты редактор крипто-канала в Telegram.
Создай 1 интересный пост на русском языке на основе этих новостей.
- Начни с эмодзи и заголовка
- 2-3 предложения о сути
- Вывод для инвесторов
- 3-5 хэштегов в конце
- 150-250 слов, живой тон

Новости:
{headlines}

Верни только текст поста."""}]
    )
    return resp.content[0].text.strip()

# ─── ПУБЛИКАЦИЯ ───────────────────────────────────────────────────────────────

async def post_to_channel(bot: Bot):
    log.info("Запуск публикации...")
    news = get_news()
    if not news:
        return
    post_text = ai_process_news(news)
    if not post_text:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📢 Поделиться каналом",
            url=f"https://t.me/share/url?url=https://t.me/{CHANNEL_ID.lstrip('@')}&text=Крутой+крипто+канал!"
        )
    ]])
    await bot.send_message(
        chat_id=CHANNEL_ID, text=post_text,
        reply_markup=keyboard, parse_mode="HTML",
        disable_web_page_preview=True,
    )
    log.info(f"Опубликовано в {CHANNEL_ID}")

# ─── КОМАНДЫ ──────────────────────────────────────────────────────────────────

async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Бот работает!\n\n"
        "📰 Telegram канал:\n"
        "/post — опубликовать пост сейчас\n"
        "/schedule — расписание\n\n"
        "🐦 X (Twitter):\n"
        "/x_post [тема] — пост для X\n"
        "/x_thread [тема] — тред для X\n"
        "/x_reply текст — комментарий под пост\n"
        "/x_ideas — идеи для постов на сегодня\n\n"
        "🤝 Взаимопиар:\n"
        "/promo_offer — текст предложения партнёрам\n"
        "/add_partner @канал Описание — добавить партнёра\n"
        "/partners — список партнёров\n"
        "/post_partner @канал — пост о партнёре\n"
        "/promo_stats — статистика"
    )

async def cmd_post_now(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Генерирую пост...")
    await post_to_channel(context.bot)
    await update.message.reply_text("✅ Опубликовано!")

async def cmd_schedule(update, context: ContextTypes.DEFAULT_TYPE):
    times = "\n".join(f"• {s['hour']:02d}:{s['minute']:02d}" for s in SCHEDULE)
    await update.message.reply_text(f"📅 Расписание:\n{times}")

# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("post", cmd_post_now))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    register_promo_handlers(app)
    register_x_handlers(app)  # модуль X  # подключаем взаимопиар

    scheduler = AsyncIOScheduler()
    for s in SCHEDULE:
        scheduler.add_job(post_to_channel, "cron", hour=s["hour"], minute=s["minute"], args=[app.bot])
    scheduler.start()

    log.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

