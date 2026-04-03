import os
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai
from promo_helper import register_promo_handlers
from x_helper import register_x_handlers

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY", "")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

SCHEDULE = [
    {"hour": 9,  "minute": 0},
    {"hour": 13, "minute": 0},
    {"hour": 18, "minute": 0},
    {"hour": 21, "minute": 0},
]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


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


def ai_process_news(news_items):
    if not news_items:
        return None
    headlines = "\n".join(f"{i+1}. {n['title']} ({n['url']})" for i, n in enumerate(news_items))
    
    # Настройка Gemini
    genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    prompt = (
        "Ты редактор крипто-канала в Telegram.\n"
        "Создай 1 интересный пост на русском языке на основе этих новостей.\n"
        "- Начни с эмодзи и заголовка\n"
        "- 2-3 предложения о сути\n"
        "- Вывод для инвесторов\n"
        "- 3-5 хэштегов в конце\n"
        "- 150-250 слов, живой тон\n\n"
        f"Новости:\n{headlines}\n\n"
        "Верни только текст поста."
    )
    response = model.generate_content(prompt)
    return response.text.strip()


async def post_to_channel(context):
    bot = context.bot
    log.info("Запуск публикации...")
    news = get_news()
    if not news:
        return
    post_text = ai_process_news(news)
    if not post_text:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "Поделиться каналом",
            url="https://t.me/share/url?url=https://t.me/" + CHANNEL_ID.lstrip("@") + "&text=Крутой крипто канал!"
        )
    ]])
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=post_text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    log.info("Опубликовано в " + CHANNEL_ID)


async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot rabotaet!\n\n"
        "Kontent:\n"
        "/post - opublikovat post seychas\n"
        "/schedule - raspisanie\n\n"
        "X (Twitter):\n"
        "/x_post - post dlya X\n"
        "/x_thread - tred dlya X\n"
        "/x_reply tekst - kommentariy\n"
        "/x_ideas - idei dlya postov\n\n"
        "Vzaimopiar:\n"
        "/promo_offer - tekst predlozheniya\n"
        "/add_partner kanal - dobavit partnera\n"
        "/partners - spisok partnerov\n"
        "/post_partner kanal - post o partnere\n"
        "/promo_stats - statistika"
    )


async def cmd_post_now(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generiruyu post...")
    await post_to_channel(context)
    await update.message.reply_text("Opublikovano!")


async def cmd_schedule(update, context: ContextTypes.DEFAULT_TYPE):
    times = "\n".join(f"{s['hour']:02d}:{s['minute']:02d}" for s in SCHEDULE)
    await update.message.reply_text("Raspisanie:\n" + times)


def main():
    if not GOOGLE_GEMINI_API_KEY:
        log.error("GOOGLE_GEMINI_API_KEY ne zadana!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("post", cmd_post_now))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    register_promo_handlers(app)
    register_x_handlers(app)

    # Планировщик через job_queue
    for s in SCHEDULE:
        app.job_queue.run_daily(
            post_to_channel,
            time=__import__("datetime").time(hour=s["hour"], minute=s["minute"])
        )

    log.info("Bot zapuschen!")
    app.run_polling()


if __name__ == "__main__":
    main()
