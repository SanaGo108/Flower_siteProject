import sys
import os
import logging
from asgiref.sync import sync_to_async

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
        user_name = query.from_user.username
        user_id = query.from_user.id  # Идентификатор пользователя в Телеграм

        logger.info(f"Кнопка нажата: {query.data} от пользователя: {user_name} ({user_id})")
        await query.answer()

        if query.data == "register":
            await query.message.reply_text(f"Привет, {user_name}! Вы успешно зарегистрированы.")
        elif query.data == "my_order":
            # Проверка наличия заказов пользователя
            orders = await sync_to_async(list)(
                Order.objects.filter(telegram_username=user_name).prefetch_related("orderitem_set")
            )

            if not orders:
                # Альтернативная проверка по user_id или другому параметру
                orders_by_id = await sync_to_async(list)(
                    Order.objects.filter(user_id=user_id).prefetch_related("orderitem_set")
                )

                if not orders_by_id:
                    await query.message.reply_text("У вас пока нет заказов.")
                    return
                orders = orders_by_id

            # Отправка данных о заказах
            for order in orders:
                for item in order.orderitem_set.all():
                    photo_url = item.flower.image.url if item.flower.image else None
                    caption = (f"\ud83c\udf38 Букет: {item.flower.name}\n"
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

# Функция для отправки уведомления о новом заказе
async def send_order_notification(order):
    try:
        logger.info(f"Отправка уведомления о заказе: {order}")
        caption = f"\ud83d\uded2 Новый заказ!\n"
        caption += f"\ud83d\udd11 Номер заказа: {order.id}\n"
        caption += f"\ud83d\udcc5 Дата доставки: {order.delivery_date}\n"
        caption += f"\ud83d\udd52 Время доставки: {order.delivery_time}\n"
        caption += f"\ud83c\udfe1 Адрес: {order.delivery_address}\n\n"

        for item in order.orderitem_set.all():
            item_caption = (f"\ud83c\udf38 {item.flower.name} - {item.quantity} шт. x ₽{item.flower.price} = ₽{item.quantity * item.flower.price}\n")
            caption += item_caption

        caption += f"\n\ud83d\udcb5 Общая стоимость: ₽{order.total_price}"

        # Отправка сообщения боту (замените CHAT_ID на ID чата бота или пользователя)
        await Application.builder().token(BOT_TOKEN).build().bot.send_message(chat_id=order.telegram_username, text=caption)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о заказе: {e}")

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