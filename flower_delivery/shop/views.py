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

# ✅ Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Установка пути к проекту Django
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_path not in sys.path:
    sys.path.append(project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')

# ✅ Настройка Django окружения
try:
    import django
    django.setup()
except Exception as e:
    logger.error(f"Ошибка при настройке Django: {e}")
    raise

# ✅ Импорт моделей
Profile = apps.get_model('shop', 'Profile')
Order = apps.get_model('shop', 'Order')
OrderItem = apps.get_model('shop', 'OrderItem')
Flower = apps.get_model('shop', 'Flower')

# ✅ Токен бота
BOT_TOKEN = '7558727339:AAFkPjY1BSCHYBoNW5fOtDmuNDYz90kvYYA'  # 🔥 ВСТАВЬ СВОЙ ТОКЕН
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ✅ Главное меню
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

# ✅ Обработчик кнопок
@dp.callback_query_handler()
async def handle_callback(query: types.CallbackQuery):
    user_name = query.from_user.username  # Получаем Telegram username
    logger.info(f"🔹 Кнопка нажата: {query.data} от пользователя: {user_name}")

    if query.data == "register":
        await query.message.answer(f"Привет, {user_name}! Вы успешно зарегистрированы.")

    elif query.data == "my_order":
        await handle_my_order(query, user_name)

    elif query.data == "payment":
        await query.message.answer("Перейдите на страницу оплаты: http://127.0.0.1:8000/payment/")

    elif query.data == "help":
        await query.message.answer("Свяжитесь с менеджером по телефону: +7 123 456 78 90")

# ✅ Исправленный обработчик "Мой заказ"
async def handle_my_order(query, user_name):
    try:
        if not user_name:
            await query.message.answer("❌ Ваш Telegram аккаунт не имеет username. Добавьте его в Telegram!")
            return

        # 🔥 Убираем `@` и ищем профиль (асинхронно!)
        profile = await sync_to_async(lambda: Profile.objects.filter(telegram_username__iexact=user_name).first())()
        if not profile:
            profile = await sync_to_async(lambda: Profile.objects.filter(telegram_username__iexact=f"@{user_name}").first())()

        if not profile:
            await query.message.answer("❌ Ваш профиль не найден. Укажите Telegram username в профиле сайта.")
            return

        # ✅ Получаем пользователя Django (асинхронно)
        user = await sync_to_async(lambda: profile.user)()

        # ✅ Ищем заказы (асинхронно!)
        orders = await sync_to_async(lambda: list(Order.objects.filter(user=user).prefetch_related("orderitem_set")))()

        if not orders:
            await query.message.answer("📭 У вас пока нет заказов.")
            return

        # ✅ Отправляем информацию о заказах
        for order in orders:
            items = await sync_to_async(lambda: list(order.orderitem_set.all()))()
            items_text = "\n".join(
                [f"🌸 {await sync_to_async(lambda: item.flower.name)()} - {item.quantity} шт." for item in items]
            )
            message = (
                f"🛒 *Заказ #{order.id}*\n"
                f"📅 Дата доставки: {order.delivery_date}\n"
                f"⏰ Время: {order.delivery_time}\n"
                f"📍 Адрес: {order.delivery_address}\n"
                f"💰 Итог: ₽{order.total_price}\n"
                f"\n📦 *Товары:* \n{items_text}"
            )

            await query.message.answer(message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка при получении заказов: {e}")
        await query.message.answer("⚠️ Произошла ошибка при получении ваших заказов.")

# ✅ Функция отправки уведомления
async def send_order_notification(telegram_username, items, total_price, delivery_address, delivery_time, comment):
    try:
        user = await bot.get_chat(telegram_username)
        chat_id = user.id

        message = f"🛒 *Ваш заказ*\n\n"
        for item in items:
            message += f"🌸 {item['name']} - {item['quantity']} шт. x ₽{item['price']} = ₽{item['total']}\n"
        message += f"\n💰 *Общая стоимость:* ₽{total_price}\n📍 Адрес: {delivery_address}\n⏰ Время: {delivery_time}\n✍ Комментарий: {comment}"

        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

        for item in items:
            if item["photo"]:
                await bot.send_photo(chat_id=chat_id, photo=item["photo"])

    except Exception as e:
        logging.error(f"❌ Ошибка при отправке уведомления: {e}")

# ✅ Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

