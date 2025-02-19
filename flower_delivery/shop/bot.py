import sys
import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps

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

Profile = apps.get_model('shop', 'Profile')
Order = apps.get_model('shop', 'Order')

BOT_TOKEN = '7558727339:AAFkPjY1BSCHYBoNW5fOtDmuNDYz90kvYYA'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Регистрация", callback_data="register"),
        InlineKeyboardButton("Мой заказ", callback_data="my_order"),
        InlineKeyboardButton("Помощь менеджера", callback_data="help"),
        InlineKeyboardButton("Оплата заказа", callback_data="payment"),
    )
    await message.answer("Здравствуйте, это бот-помощник FlowerDelivery. Выберите действие:", reply_markup=keyboard)


# Обработка кнопок
@dp.callback_query_handler()
async def handle_callback(query: types.CallbackQuery):
    user_name = query.from_user.username
    logger.info(f"Кнопка нажата: {query.data} от пользователя: {user_name}")

    if query.data == "register":
        await query.message.answer(f"Привет, {user_name}! Вы успешно зарегистрированы.")

    elif query.data == "my_order":
        # Проверяем оба варианта Telegram username (@username и username)
        profile = await sync_to_async(Profile.objects.filter(telegram_username__iexact=user_name).first)()
        if not profile:
            profile = await sync_to_async(Profile.objects.filter(telegram_username__iexact=f"@{user_name}").first)()

        if not profile:
            await query.message.answer("Ваш профиль не найден. Пожалуйста, зарегистрируйтесь на сайте.")
            return

        # Получаем пользователя
        user = await sync_to_async(lambda: profile.user)()

        # ⚡ Исправленный `async` запрос на поиск заказов ⚡
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).prefetch_related("orderitem_set")))()

        if not orders:
            await query.message.answer("У вас пока нет заказов.")
            return

        for order in orders:
            items = []
            for item in order.orderitem_set.all():
                photo_url = item.flower.image.url if item.flower.image else None
                items.append({
                    "name": item.flower.name,
                    "quantity": item.quantity,
                    "price": item.flower.price,
                    "total": item.quantity * item.flower.price,
                    "photo": photo_url
                })

            await send_order_notification(user_name, items, sum(i["total"] for i in items))

    elif query.data == "payment":
        await query.message.answer("Перейдите на страницу оплаты: http://127.0.0.1:8000/payment/")
    elif query.data == "help":
        await query.message.answer("Свяжитесь с менеджером по телефону: +7 123 456 78 90")


# Функция отправки уведомления
async def send_order_notification(telegram_username, items, total_price, delivery_address, delivery_time, comment):
    try:
        # ✅ Убираем "@" в Telegram username, если он есть
        telegram_username = telegram_username.replace("@", "")

        # ✅ Проверяем, может ли бот найти пользователя
        user = await bot.get_chat(telegram_username)
        chat_id = user.id

        message = f"🛒 *Ваш заказ*\n\n"
        for item in items:
            message += f"🌸 {item['name']} - {item['quantity']} шт. x ₽{item['price']} = ₽{item['total']}\n"
        message += f"\n💰 *Общая стоимость:* ₽{total_price}\n"

        await bot.send_message(chat_id=f"@{telegram_username}", text=message, parse_mode="Markdown")

        for item in items:
            if item["photo"]:
                await bot.send_photo(chat_id=f"@{telegram_username}", photo=item["photo"])

    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")


# Запуск бота через `asyncio`
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



