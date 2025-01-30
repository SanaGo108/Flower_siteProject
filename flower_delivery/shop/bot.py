import sys
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from asgiref.sync import sync_to_async


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Установка пути к проекту
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_path not in sys.path:
    sys.path.append(project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.flower_delivery.settings')


# Установка Django окружения
try:
    import django
    django.setup()
except Exception as e:
    logger.error(f"Ошибка при настройке Django: {e}")
    raise

from shop.models import Order, OrderItem

BOT_TOKEN = '7558727339:AAFkPjY1BSCHYBoNW5fOtDmuNDYz90kvYYA'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    try:
        logger.info("Команда /start вызвана")
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Регистрация", callback_data="register"),
            InlineKeyboardButton("Мой заказ", callback_data="my_order"),
            InlineKeyboardButton("Помощь менеджера", callback_data="help"),
            InlineKeyboardButton("Оплата заказа", callback_data="payment"),
        )
        await message.answer("Здравствуйте, это бот-помощник FlowerDelivery. Выберите действие:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")

# Обработка нажатий кнопок
@dp.callback_query_handler()
async def handle_callback(query: types.CallbackQuery):
    try:
        user_name = query.from_user.username
        logger.info(f"Кнопка нажата: {query.data} от пользователя: {user_name}")

        if query.data == "register":
            await query.message.answer(f"Привет, {user_name}! Вы успешно зарегистрированы.")
        elif query.data == "my_order":
            orders = await sync_to_async(list)(
                Order.objects.filter(telegram_username=user_name).prefetch_related("orderitem_set")
            )

            if not orders:
                await query.message.answer("У вас пока нет заказов.")
                return

            for order in orders:
                for item in order.orderitem_set.all():
                    photo_url = item.flower.image.url if item.flower.image else None
                    caption = (
                        f"🌸 Букет: {item.flower.name}\n"
                        f"Количество: {item.quantity}\n"
                        f"Стоимость: ₽{item.quantity * item.flower.price}"
                    )
                    if photo_url:
                        await bot.send_photo(chat_id=query.from_user.id, photo=photo_url, caption=caption)
                    else:
                        await bot.send_message(chat_id=query.from_user.id, text=caption)
        elif query.data == "payment":
            await query.message.answer("Перейдите на страницу оплаты: http://127.0.0.1:8000/payment/")
        elif query.data == "help":
            await query.message.answer("Свяжитесь с нашим менеджером по телефону: +7 123 456 78 90")
    except Exception as e:
        logger.error(f"Ошибка в обработке callback: {e}")

# Отправка уведомления о новом заказе
async def send_order_notification(telegram_username, items, total_price):
    try:
        message = "🛒 *Новый заказ*\n\n"
        for item in items:
            message += (
                f"🌸 {item['name']} - {item['quantity']} шт. x ₽{item['price']} = ₽{item['total']}\n"
            )
        message += f"\n💰 *Общая стоимость:* ₽{total_price}\n"
        message += f"\n📍 *Адрес доставки:* {items[0].get('delivery_address', 'Не указан')}\n"
        message += f"🕒 *Время доставки:* {items[0].get('delivery_time', 'Не указано')}\n"
        message += f"💬 *Комментарий:* {items[0].get('comment', 'Нет комментария')}\n"

        await bot.send_message(chat_id=f"@{telegram_username}", text=message, parse_mode="Markdown")

        for item in items:
            if item["photo"]:
                await bot.send_photo(chat_id=f"@{telegram_username}", photo=item["photo"])

    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")


# Запуск бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)