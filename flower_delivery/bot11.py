import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from aiogram.client.bot import DefaultBotProperties


# Допустим, вам нужен доступ к моделям Django:
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_delivery.settings")
import django
django.setup()

from shop.models import Order, OrderItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOU_TOKEN"

# Создаём бота и диспетчер (aiogram 3):
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# ======== Хендлеры ========

async def cmd_start(message: Message):
    """
    Обработчик для /start
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Регистрация", callback_data="register"),
         InlineKeyboardButton(text="Мой заказ", callback_data="my_order")],
        [InlineKeyboardButton(text="Помощь менеджера", callback_data="help"),
         InlineKeyboardButton(text="Оплата заказа", callback_data="payment")]
    ])
    await message.answer("Здравствуйте, это бот-помощник FlowerDelivery. Выберите действие:", reply_markup=keyboard)

async def handle_callback(query: CallbackQuery):
    """
    Обработчик для нажатий на inline-кнопки
    """
    user_name = query.from_user.username
    logger.info(f"Кнопка нажата: {query.data} от пользователя: {user_name}")

    if query.data == "register":
        await query.message.answer(f"Привет, {user_name}! Вы успешно зарегистрированы.")
    elif query.data == "my_order":
        # Используем sync_to_async для обращения к БД Django
        orders = await sync_to_async(list)(
            Order.objects.filter(telegram_username=user_name).prefetch_related("orderitem_set")
        )
        if not orders:
            await query.message.answer("У вас пока нет заказов.")
        else:
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

async def send_order_notification(telegram_username: str, items: list, total_price: float):
    """
    Отправка уведомления о новом заказе
    """
    try:
        message_text = "🛒 Новый заказ:\n"
        for item in items:
            message_text += (
                f"🌸 {item['name']} - {item['quantity']} шт. x ₽{item['price']} = ₽{item['total']}\n"
            )
        message_text += f"\n💰 Общая стоимость: ₽{total_price}"

        await bot.send_message(chat_id=f"@{telegram_username}", text=message_text)
        for item in items:
            if item.get("photo"):
                await bot.send_photo(chat_id=f"@{telegram_username}", photo=item["photo"])
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления: {e}")


# ======== Регистрация хендлеров в Dispatcher ========
def register_handlers():
    # Хендлер на команду /start
    dp.message.register(cmd_start, Command(commands=["start"]))

    # Хендлер на все callback_data (вместо @dp.callback_query_handler)
    dp.callback_query.register(handle_callback)

async def main():
    register_handlers()
    # Запускаем бота (long-polling)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
