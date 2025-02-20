import json
import logging
import sys
import os
import asyncio
import traceback

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib import messages
from django.utils.crypto import get_random_string
from asgiref.sync import sync_to_async  # ✅ Добавлено для асинхронных операций
from shop.bot import send_order_notification  # ✅ Исправленный импорт

from .models import Order, OrderItem, Flower, CartItem, Profile
from .forms import CustomUserCreationForm

# Настройка логирования
logger = logging.getLogger(__name__)

### ✅ ДОБАВЛЕНА ФУНКЦИЯ HOME, чтобы исправить ошибку "AttributeError: module 'shop.views' has no attribute 'home'"
def home(request):
    return render(request, 'shop/home.html')

def catalog(request):
    flowers = Flower.objects.all()
    return render(request, 'shop/catalog.html', {'flowers': flowers})

# Функция для проверки, является ли пользователь администратором
def is_admin(user):
    return user.is_authenticated and user.is_superuser

@login_required
def success_page(request):
    """Страница успешного оформления заказа"""
    return render(request, 'shop/success_page.html')

@login_required
def payment(request):
    """Страница оплаты"""
    return render(request, 'shop/payment.html')

@user_passes_test(is_admin, login_url='/accounts/login/')
def admin_panel(request):
    return render(request, 'admin_panel.html')

@login_required
def cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total_price = sum(item.quantity * item.flower.price for item in cart_items)
    return render(request, 'shop/cart.html', {"cart": cart_items, "cart_total": total_price})

@login_required
def checkout(request):
    if request.method == 'POST':
        logger.info(f"📌 Данные из формы: {request.POST}")

        try:
            user = request.user
            profile, _ = Profile.objects.get_or_create(user=user)

            # Проверяем наличие `chat_id`
            if not profile.chat_id:
                messages.error(request, "Ошибка: Укажите ваш Telegram chat_id в профиле.")
                return redirect('profile')

            # Получаем данные заказа
            delivery_date = request.POST.get('delivery_date', '').strip()
            delivery_time = request.POST.get('delivery_time', '').strip()
            delivery_address = request.POST.get('delivery_address', '').strip()
            comment = request.POST.get('comment', '').strip()

            if not all([delivery_date, delivery_time, delivery_address]):
                messages.error(request, "Заполните все обязательные поля.")
                return redirect('checkout')

            cart_items = CartItem.objects.filter(user=user)
            if not cart_items.exists():
                messages.error(request, "Корзина пуста. Добавьте товары перед оформлением заказа.")
                return redirect('cart')

            # Создаём заказ
            order = Order.objects.create(
                user=user,
                chat_id=profile.chat_id,
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                delivery_address=delivery_address,
                comment=comment
            )

            items_data = []
            total_price = 0

            for item in cart_items:
                OrderItem.objects.create(order=order, flower=item.flower, quantity=item.quantity)
                items_data.append({
                    "name": item.flower.name,
                    "quantity": item.quantity,
                    "price": item.flower.price,
                    "total": item.quantity * item.flower.price,
                    "photo": item.flower.image.url if item.flower.image else None,
                })
                total_price += item.quantity * item.flower.price

            # Обновляем цену заказа
            order.total_price = total_price
            order.save()

            # Очищаем корзину
            cart_items.delete()

            # ✅ Отправляем уведомление в Telegram с chat_id
            asyncio.run(send_order_notification(profile.chat_id, items_data, total_price, delivery_address, delivery_time, comment))

            messages.success(request, "Заказ успешно оформлен!")
            return redirect('success_page')

        except Exception as e:
            logger.error(f"🚨 Ошибка при оформлении заказа: {str(e)}", exc_info=True)
            messages.error(request, f"Произошла ошибка: {str(e)}")
            return redirect('checkout')

    return render(request, 'shop/checkout.html')


@login_required
@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            flower_id = data.get("id")
            quantity = int(data.get("quantity", 1))

            flower = Flower.objects.get(id=flower_id)
            cart_item, created = CartItem.objects.get_or_create(
                flower=flower,
                user=request.user
            )
            cart_item.quantity += quantity if not created else quantity
            cart_item.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Некорректный метод запроса."})

@login_required
def profile(request):
    if request.method == "POST":
        chat_id = request.POST.get("chat_id", "").strip()
        if chat_id:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.chat_id = chat_id
            profile.save()
            messages.success(request, "Chat ID успешно обновлен!")
        else:
            messages.error(request, "Введите корректный chat_id.")
        return redirect("profile")  # ✅ Перенаправление, чтобы обновить страницу

    return render(request, "shop/profile.html")



def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                telegram_username = request.POST.get("telegram_username", "").strip()
                if not telegram_username:
                    telegram_username = f"tg_{get_random_string(10)}"
                profile.telegram_username = telegram_username
                profile.save()
            else:
                messages.warning(request, "Профиль уже существует для данного пользователя.")

            login(request, user)
            messages.success(request, "Вы успешно зарегистрировались!")
            return redirect('home')
        else:
            messages.error(request, "Ошибка регистрации. Проверьте введенные данные.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'shop/register.html', {'form': form})

@login_required
@csrf_exempt
def update_cart(request):
    """Обновление количества товаров в корзине"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            flower_id = data.get("id")
            quantity = int(data.get("quantity", 1))

            cart_item = CartItem.objects.get(flower_id=flower_id, user=request.user)

            if quantity < 1:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()

            return JsonResponse({"success": True})
        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "Товар не найден."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Некорректный метод запроса."})

@login_required
@csrf_exempt
def send_to_bot(request):
    """Отправка заказа в Telegram-бот"""
    if request.method == 'POST':
        try:
            user = request.user
            cart_items = CartItem.objects.filter(user=user)

            if not cart_items.exists():
                return JsonResponse({"success": False, "error": "Корзина пуста."})

            items = []
            total_price = 0
            for item in cart_items:
                items.append({
                    "name": item.flower.name,
                    "quantity": item.quantity,
                    "price": item.flower.price,
                    "total": item.quantity * item.flower.price,
                    "photo": item.flower.image.url if item.flower.image else None,
                })
                total_price += item.quantity * item.flower.price

            telegram_username = getattr(user.profile, 'telegram_username', None)
            if not telegram_username:
                return JsonResponse({"success": False, "error": "Telegram username не найден. Укажите его в профиле."})

            # Запуск асинхронной задачи
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                send_order_notification(telegram_username, items, total_price), loop
            )

            return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Ошибка при отправке заказа в бота: {e}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Некорректный метод запроса."})



