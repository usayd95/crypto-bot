"""
Модуль взаимопиара для крипто-канала
======================================
Помогает автоматически формировать предложения о взаимопиаре
и отслеживать партнёров.

Использование:
    from promo_helper import PromoHelper
    promo = PromoHelper(bot, CHANNEL_ID)
"""

import json
import os
import logging
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

log = logging.getLogger(__name__)

# ─── ФАЙЛ ДЛЯ ХРАНЕНИЯ ПАРТНЁРОВ ────────────────────────────────────────────

PARTNERS_FILE = "partners.json"

def load_partners() -> dict:
    if os.path.exists(PARTNERS_FILE):
        with open(PARTNERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_partners(data: dict):
    with open(PARTNERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── ШАБЛОНЫ СООБЩЕНИЙ ──────────────────────────────────────────────────────

PROMO_TEMPLATES = {
    "offer": """👋 Привет!

Веду крипто-канал {channel} — публикуем актуальные новости рынка, AI-аналитику и разборы монет.

Предлагаю взаимопиар 🤝:
• Ты публикуешь пост о нашем канале
• Мы публикуем пост о твоём канале
• Формат и время — по договорённости

Статистика нашего канала:
• Тематика: крипто / финансы
• Публикации: ежедневно, 3-4 поста
• Контент: новости + AI-аналитика

Интересно? Напиши — обсудим детали! 🚀""",

    "followup": """👋 Здравствуй снова!

Недавно писал по поводу взаимопиара наших каналов. Предложение ещё в силе 🤝

Если интересно сотрудничество — буду рад обсудить!

{channel}""",

    "post_about_partner": """🤝 Рекомендуем канал партнёра!

{partner_description}

👉 Подписывайтесь: {partner_link}

#партнёр #крипто""",
}

# ─── ФУНКЦИИ ─────────────────────────────────────────────────────────────────

def generate_offer(channel_id: str) -> str:
    """Сгенерировать текст предложения взаимопиара."""
    return PROMO_TEMPLATES["offer"].format(channel=channel_id)

def generate_followup(channel_id: str) -> str:
    """Сгенерировать текст повторного сообщения."""
    return PROMO_TEMPLATES["followup"].format(channel=channel_id)

def generate_partner_post(partner_link: str, partner_description: str) -> str:
    """Сгенерировать пост для публикации о партнёре."""
    return PROMO_TEMPLATES["post_about_partner"].format(
        partner_link=partner_link,
        partner_description=partner_description,
    )

# ─── КОМАНДЫ БОТА ────────────────────────────────────────────────────────────

async def cmd_promo_offer(update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promo_offer — показать готовый текст предложения взаимопиара.
    Скопируй и отправь администратору другого канала вручную.
    """
    channel = os.getenv("CHANNEL_ID", "@твой_канал")
    text = generate_offer(channel)

    await update.message.reply_text(
        f"📋 Готовый текст для предложения взаимопиара:\n\n"
        f"<code>{text}</code>\n\n"
        "👆 Скопируй и отправь администратору нужного канала.",
        parse_mode="HTML"
    )


async def cmd_add_partner(update, context: ContextTypes.DEFAULT_TYPE):
    """
    /add_partner @канал Описание — добавить партнёра в список.
    Пример: /add_partner @bitcoin_news Лучший канал про биткоин
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /add_partner @канал Описание\n"
            "Пример: /add_partner @bitcoin_news Лучший канал про биткоин"
        )
        return

    partner_link = args[0]
    description = " ".join(args[1:])

    partners = load_partners()
    partners[partner_link] = {
        "description": description,
        "added": datetime.now().isoformat(),
        "active": True,
    }
    save_partners(partners)

    await update.message.reply_text(
        f"✅ Партнёр {partner_link} добавлен!\n\n"
        f"Используй /post_partner {partner_link} чтобы опубликовать пост о нём."
    )


async def cmd_list_partners(update, context: ContextTypes.DEFAULT_TYPE):
    """/partners — показать список партнёров."""
    partners = load_partners()
    if not partners:
        await update.message.reply_text("Партнёров пока нет. Добавь через /add_partner")
        return

    lines = ["📋 Список партнёров:\n"]
    for link, data in partners.items():
        status = "✅" if data.get("active") else "⏸"
        lines.append(f"{status} {link} — {data['description']}")

    await update.message.reply_text("\n".join(lines))


async def cmd_post_partner(update, context: ContextTypes.DEFAULT_TYPE):
    """
    /post_partner @канал — опубликовать пост о партнёре в канал.
    """
    if not context.args:
        await update.message.reply_text("Использование: /post_partner @канал")
        return

    partner_link = context.args[0]
    partners = load_partners()

    if partner_link not in partners:
        await update.message.reply_text(
            f"Партнёр {partner_link} не найден. Сначала добавь через /add_partner"
        )
        return

    description = partners[partner_link]["description"]
    post_text = generate_partner_post(partner_link, description)

    channel = os.getenv("CHANNEL_ID", "@твой_канал")
    await context.bot.send_message(
        chat_id=channel,
        text=post_text,
        parse_mode="HTML",
    )

    await update.message.reply_text(f"✅ Пост о {partner_link} опубликован в канал!")


async def cmd_promo_stats(update, context: ContextTypes.DEFAULT_TYPE):
    """/promo_stats — статистика по взаимопиару."""
    partners = load_partners()
    total = len(partners)
    active = sum(1 for p in partners.values() if p.get("active"))

    await update.message.reply_text(
        f"📊 Статистика взаимопиара:\n\n"
        f"• Всего партнёров: {total}\n"
        f"• Активных: {active}\n\n"
        f"Команды:\n"
        f"/promo_offer — текст предложения\n"
        f"/add_partner — добавить партнёра\n"
        f"/partners — список партнёров\n"
        f"/post_partner — опубликовать пост о партнёре"
    )


# ─── РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ───────────────────────────────────────────────────

def register_promo_handlers(app):
    """Подключить все команды взаимопиара к боту."""
    app.add_handler(CommandHandler("promo_offer", cmd_promo_offer))
    app.add_handler(CommandHandler("add_partner", cmd_add_partner))
    app.add_handler(CommandHandler("partners", cmd_list_partners))
    app.add_handler(CommandHandler("post_partner", cmd_post_partner))
    app.add_handler(CommandHandler("promo_stats", cmd_promo_stats))
    log.info("Модуль взаимопиара подключён.")
      
