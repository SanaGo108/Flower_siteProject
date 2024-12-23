import sys
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Установка пути к проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')

# Установка Django окружения
import django
django.setup()

from shop.models import Order, OrderItem
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

BOT_TOKEN = '7558727339:AAFkPjY1BSCHYBoNW5fOtDmuNDYz90kvYYA'

# Функция для обработки команды /start
async def start(update, context):
    try:
        logger.info("Команда /start вызвана")
        keyboard = [
            [InlineKeyboardButton("Регистрация", callback_data="register")],
            [InlineKeyboardButton("Мой заказ", callback_data="my_order")],
            [InlineKeyboardButton("Помощь менеджера", callback_data="help")],
            [InlineKeyboardButton("Оплата заказа", callback_data="payment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Здравствуйте, это бот-помощник FlowerDelivery. Выберите действие:",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")

# Функция для обработки нажатий кнопок
async def handle_callback(update, context):
    try:
        query = update.callback_query
        user_name = query.from_user.username or "Гость"

        logger.info(f"Кнопка нажата: {query.data}")
        await query.answer()

        if query.data == "register":
            await query.message.reply_text(f"Привет, {user_name}! Вы успешно зарегистрированы.")
        elif query.data == "my_order":
            # Проверка наличия заказов пользователя
            orders = Order.objects.filter(telegram_username=user_name).prefetch_related("orderitem_set")
            if not orders.exists():
                await query.message.reply_text("У вас пока нет заказов.")
                return

            # Отправка данных о заказах
            for order in orders:
                for item in order.orderitem_set.all():
                    photo_url = item.flower.image.url if item.flower.image else None
                    caption = (f"🌸 Букет: {item.flower.name}\n"
                               f"Количество: {item.quantity}\n"
                               f"Стоимость: ₽{item.quantity * item.flower.price}")
                    if photo_url:
                        await query.message.reply_photo(photo=photo_url, caption=caption)
                    else:
                        await query.message.reply_text(caption)
        elif query.data == "payment":
            await query.message.reply_text("Перейдите на страницу оплаты: http://127.0.0.1:8000/payment/")
        elif query.data == "help":
            await query.message.reply_text("Свяжитесь с нашим менеджером по телефону: +7 123 456 78 90")
    except Exception as e:
        logger.error(f"Ошибка в обработке callback: {e}")

# Функция для настройки и запуска бота
def setup_bot():
    try:
        logger.info("Запуск бота...")
        application = Application.builder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_callback))

        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    setup_bot()

