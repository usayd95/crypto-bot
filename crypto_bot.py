import os
import logging
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import anthropic
from promo_helper import register_promo_handlers
from x_helper import register_x_handlers

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
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
        log.warning("CryptoPanic: " + str(e))
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
        log.warning("RSS: " + str(e))
        return []


def get_news():
    return (fetch_news_cryptopanic() if CRYPTOPANIC_API_KEY else []) or fetch_news_rss()


def ai_process_news(news_items):
    if not news_items:
        return None
    headlines = "\n".join(str(i+1) + ". " + n["title"] for i, n in enumerate(news_items))
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": (
            "Ty redaktor kripto-kanala v Telegram.\n"
            "Sozdaj 1 interesnyj post na russkom na osnove etih novostej.\n"
            "- Nachni s emoji i zagolovka\n"
            "- 2-3 predlozheniya o suti\n"
            "- Vyvod dlya investorov\n"
            "- 3-5 heshtegow v konce\n\n"
            "Novosti:\n" + headlines + "\n\nVerni tolko tekst posta."
        )}]
    )
    return resp.content[0].text.strip()


async def post_to_channel(context):
    bot = context.bot
    log.info("Zapusk publikacii...")
    news = get_news()
    if not news:
        return
    post_text = ai_process_news(news)
    if not post_text:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "Podelitsya kanalom",
            url="https://t.me/share/url?url=https://t.me/" + CHANNEL_ID.lstrip("@")
        )
    ]])
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=post_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    log.info("Opublikovano v " + CHANNEL_ID)


async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot rabotaet!\n\n"
        "/post - opublikovat post seychas\n"
        "/schedule - raspisanie\n"
        "/x_post - post dlya X\n"
        "/x_thread - tred dlya X\n"
        "/x_reply tekst - kommentariy\n"
        "/x_ideas - idei\n"
        "/promo_offer - predlozhenie partneram\n"
        "/partners - spisok partnerov"
    )


async def cmd_post_now(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generiruyu post...")
    await post_to_channel(context)
    await update.message.reply_text("Opublikovano!")


async def cmd_schedule(update, context: ContextTypes.DEFAULT_TYPE):
    times = "\n".join(str(s["hour"]) + ":00" for s in SCHEDULE)
    await update.message.reply_text("Raspisanie:\n" + times)


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("post", cmd_post_now))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    register_promo_handlers(app)
    register_x_handlers(app)

    # Pravilnyj sposob zapuska planirovshhika cherez JobQueue
    for s in SCHEDULE:
        app.job_queue.run_daily(
            post_to_channel,
            time=__import__("datetime").time(hour=s["hour"], minute=s["minute"])
        )

    log.info("Bot zapuschen!")
    app.run_polling()


if __name__ == "__main__":
    main()
            
