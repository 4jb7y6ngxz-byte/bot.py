"""
Telegram Stars Shop Bot
Бот для продажи звёзд Telegram через подарки
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────────

BOT_TOKEN = "8709816915:AAGuNwX-Zc_RSCnxSKgieqb8ZuPuyWKieyw"
ADMIN_ID = 8411878656
ADMIN_USERNAME = "@cryptosendik"

# Реквизиты для оплаты
CARD_NUMBER = "2200 1234 5678 9012"  # номер карты
CARD_BANK = "Сбербанк"

# ─── ПРАЙС-ЛИСТ ───────────────────────────────────────────────────────────────
# Формат: "название": {"stars": кол-во_звёзд, "price": цена_руб, "emoji": эмодзи}

CATALOG = {
    "rose_25": {
        "name": "Роза 🌹",
        "stars": 25,
        "price": 35,
        "emoji": "🌹",
        "description": "Подарок «Роза» — 25 звёзд"
    },
    "bear_50": {
        "name": "Мишка 🧸",
        "stars": 50,
        "price": 65,
        "emoji": "🧸",
        "description": "Подарок «Мишка» — 50 звёзд"
    },
    "cake_100": {
        "name": "Торт 🎂",
        "stars": 100,
        "price": 120,
        "emoji": "🎂",
        "description": "Подарок «Торт» — 100 звёзд"
    },
    "heart_250": {
        "name": "Сердце 💎",
        "stars": 250,
        "price": 280,
        "emoji": "💎",
        "description": "Подарок «Сердце» — 250 звёзд"
    },
    "crown_500": {
        "name": "Корона 👑",
        "stars": 500,
        "price": 540,
        "emoji": "👑",
        "description": "Подарок «Корона» — 500 звёзд"
    },
}

# ─── СОСТОЯНИЯ ДИАЛОГА ────────────────────────────────────────────────────────

CHOOSING, WAITING_PAYMENT, ADMIN_REPLY = range(3)

# ─── ЛОГИРОВАНИЕ ──────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище активных заказов (в памяти; для прода используй БД)
# { user_id: {"item_key": ..., "username": ..., "status": ...} }
orders = {}


# ─── КЛАВИАТУРЫ ───────────────────────────────────────────────────────────────

def main_menu_keyboard():
    """Главное меню."""
    buttons = [
        [InlineKeyboardButton("🛍 Купить звёзды", callback_data="catalog")],
        [InlineKeyboardButton("📖 Как это работает?", callback_data="howto")],
        [InlineKeyboardButton("💬 Написать администратору", callback_data="contact_admin")],
    ]
    return InlineKeyboardMarkup(buttons)


def catalog_keyboard():
    """Каталог товаров."""
    buttons = []
    for key, item in CATALOG.items():
        label = f"{item['emoji']} {item['name']} — {item['stars']}⭐ за {item['price']} руб."
        buttons.append([InlineKeyboardButton(label, callback_data=f"buy_{key}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(item_key):
    """Подтверждение покупки."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"confirm_{item_key}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="catalog")],
    ])


def payment_keyboard():
    """После подтверждения заказа."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил(а)", callback_data="paid")],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data="cancel_order")],
    ])


def admin_order_keyboard(user_id):
    """Кнопки для администратора."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"admin_confirm_{user_id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{user_id}")],
    ])


# ─── ХЭНДЛЕРЫ ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start."""
    user = update.effective_user
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🌟 *Магазин звёзд Telegram*\n\n"
        "Здесь ты можешь купить звёзды Telegram по выгодным ценам "
        "и подарить их любому пользователю в виде подарка.\n\n"
        "Выбери действие ниже 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех inline-кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # ── Главное меню ──
    if data == "back_main":
        await query.edit_message_text(
            "🌟 *Главное меню*\n\nВыбери действие:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    # ── Каталог ──
    elif data == "catalog":
        text = (
            "🛍 *Каталог звёзд*\n\n"
            "Выбери нужный подарок — звёзды будут начислены в течение *50 минут* "
            "после подтверждения оплаты.\n\n"
            "👇 Выбери товар:"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=catalog_keyboard())

    # ── Как это работает ──
    elif data == "howto":
        text = (
            "📖 *Как это работает?*\n\n"
            "1️⃣ Выбери нужное количество звёзд из каталога\n"
            "2️⃣ Подтверди заказ и переведи оплату на карту\n"
            "3️⃣ Нажми «Я оплатил(а)» — мы получим уведомление\n"
            "4️⃣ Администратор проверит оплату и свяжется с тобой\n"
            "5️⃣ Укажи нам свой @юзернейм — и мы отправим тебе подарок\n"
            "6️⃣ Подарок придёт в течение *50 минут* ⏱\n\n"
            "❓ Есть вопросы? Пиши администратору!"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="back_main")
            ]])
        )

    # ── Написать администратору напрямую ──
    elif data == "contact_admin":
        text = (
            f"💬 *Связь с администратором*\n\n"
            f"Напиши напрямую: {ADMIN_USERNAME}\n\n"
            f"⏱ Администратор отвечает в течение *15 минут*."
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="back_main")
            ]])
        )

    # ── Выбор товара из каталога ──
    elif data.startswith("buy_"):
        item_key = data[4:]
        item = CATALOG.get(item_key)
        if not item:
            await query.edit_message_text("❌ Товар не найден.")
            return

        text = (
            f"{item['emoji']} *{item['name']}*\n\n"
            f"⭐ Звёзд: *{item['stars']}*\n"
            f"💰 Цена: *{item['price']} руб.*\n\n"
            f"После оплаты подарок придёт в течение *50 минут*.\n\n"
            f"Подтверждаешь заказ?"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=confirm_keyboard(item_key)
        )

    # ── Подтверждение заказа → показ реквизитов ──
    elif data.startswith("confirm_"):
        item_key = data[8:]
        item = CATALOG.get(item_key)
        if not item:
            await query.edit_message_text("❌ Товар не найден.")
            return

        # Сохраняем заказ
        orders[user.id] = {
            "item_key": item_key,
            "item": item,
            "username": user.username or user.first_name,
            "user_id": user.id,
            "status": "waiting_payment"
        }

        text = (
            f"✅ *Заказ создан!*\n\n"
            f"📦 Товар: {item['emoji']} {item['name']} ({item['stars']}⭐)\n"
            f"💰 Сумма к оплате: *{item['price']} руб.*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 *Реквизиты для оплаты:*\n"
            f"Банк: *{CARD_BANK}*\n"
            f"Карта: `{CARD_NUMBER}`\n\n"
            f"⚠️ В комментарии к переводу ничего не пиши!\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"После перевода нажми кнопку *«Я оплатил(а)»* 👇"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=payment_keyboard()
        )

    # ── Пользователь нажал "Я оплатил(а)" ──
    elif data == "paid":
        order = orders.get(user.id)
        if not order:
            await query.edit_message_text(
                "❌ Заказ не найден. Начни заново — /start",
                reply_markup=main_menu_keyboard()
            )
            return

        item = order["item"]
        orders[user.id]["status"] = "paid"

        # Уведомляем администратора
        admin_text = (
            f"🔔 *НОВЫЙ ЗАКАЗ!*\n\n"
            f"👤 Пользователь: @{order['username']} (ID: `{user.id}`)\n"
            f"📦 Товар: {item['emoji']} {item['name']}\n"
            f"⭐ Звёзд: {item['stars']}\n"
            f"💰 Сумма: {item['price']} руб.\n\n"
            f"Пользователь сообщил об оплате. Проверь перевод и подтверди!"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_order_keyboard(user.id)
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")

        # Сообщение пользователю
        await query.edit_message_text(
            "⏳ *Спасибо! Ждём подтверждения оплаты.*\n\n"
            f"Администратор проверит перевод и свяжется с тобой.\n"
            f"⏱ Подарок придёт в течение *50 минут*.\n\n"
            f"По вопросам: {ADMIN_USERNAME}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")
            ]])
        )

    # ── Отмена заказа ──
    elif data == "cancel_order":
        orders.pop(user.id, None)
        await query.edit_message_text(
            "❌ Заказ отменён.\n\nВозвращайся, когда будешь готов!",
            reply_markup=main_menu_keyboard()
        )

    # ── Администратор: подтвердить оплату ──
    elif data.startswith("admin_confirm_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Нет доступа.", show_alert=True)
            return

        target_id = int(data[14:])
        order = orders.get(target_id)
        if not order:
            await query.edit_message_text("❌ Заказ не найден (возможно, уже обработан).")
            return

        item = order["item"]
        orders[target_id]["status"] = "confirmed"

        # Уведомляем пользователя
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"✅ *Оплата подтверждена!*\n\n"
                f"Твой заказ: {item['emoji']} {item['name']} ({item['stars']}⭐)\n\n"
                f"🎁 Подарок будет отправлен в течение *50 минут*.\n"
                f"Напиши администратору свой @юзернейм если ещё не сделал это.\n\n"
                f"Спасибо за покупку! 🌟"
            ),
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            f"✅ Заказ для @{order['username']} подтверждён!\n"
            f"Товар: {item['emoji']} {item['name']} — {item['stars']}⭐",
            parse_mode="Markdown"
        )

    # ── Администратор: отклонить ──
    elif data.startswith("admin_reject_"):
        if user.id != ADMIN_ID:
            await query.answer("⛔ Нет доступа.", show_alert=True)
            return

        target_id = int(data[13:])
        order = orders.get(target_id)
        if not order:
            await query.edit_message_text("❌ Заказ не найден.")
            return

        orders.pop(target_id, None)

        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "❌ *Оплата не подтверждена.*\n\n"
                "Возможно, перевод не поступил или произошла ошибка.\n"
                f"Свяжись с администратором: {ADMIN_USERNAME}\n\n"
                "Попробуй снова — /start"
            ),
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            f"❌ Заказ для @{order['username']} отклонён.",
        )


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin — только для администратора."""
    if update.effective_user.id != ADMIN_ID:
        return
    active = [o for o in orders.values() if o["status"] != "confirmed"]
    if not active:
        await update.message.reply_text("📭 Активных заказов нет.")
        return
    lines = ["📋 *Активные заказы:*\n"]
    for o in active:
        lines.append(
            f"• @{o['username']} — {o['item']['emoji']} {o['item']['name']} "
            f"({o['item']['stars']}⭐, {o['item']['price']}₽) — статус: {o['status']}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
