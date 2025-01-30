import json
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib import messages
from django.utils.crypto import get_random_string
from bot import send_order_notification

from .models import Order, OrderItem, Flower, CartItem, Profile
from .forms import CustomUserCreationForm
import asyncio

# Настройка логирования
logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'shop/home.html')

def catalog(request):
    flowers = Flower.objects.all()
    return render(request, 'shop/catalog.html', {'flowers': flowers})

# Функция для проверки является ли пользователь администратором
def is_admin(user):
    return user.is_authenticated and user.is_superuser

# Ограничение доступа к админ-панели только для администраторов
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
        try:
            user = request.user
            profile = Profile.objects.get(user=user)
            telegram_id = profile.telegram_id  # Используем ID Telegram

            delivery_date = request.POST.get('delivery_date')
            delivery_time = request.POST.get('delivery_time')
            delivery_address = request.POST.get('delivery_address')
            comment = request.POST.get('comment', '')

            if not all([telegram_id, delivery_date, delivery_time, delivery_address]):
                return render(request, 'shop/checkout.html', {"error": "Заполните все обязательные поля."})

            order = Order.objects.create(
                user=user,
                telegram_username=profile.telegram_username,
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                delivery_address=delivery_address,
                comment=comment,
                total_price=0,
            )

            cart_items = CartItem.objects.filter(user=user)
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

            cart_items.delete()
            order.total_price = total_price
            order.save()

            # ✅ Асинхронный вызов без блокировки
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                send_order_notification(telegram_id, items_data, total_price, delivery_address, delivery_time, comment))

            return redirect('success_page')

        except Exception as e:
            return render(request, 'shop/checkout.html', {"error": str(e)})

    return render(request, 'shop/checkout.html')


def success_page(request):
    return render(request, 'shop/success_page.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Проверяем, есть ли уже профиль для пользователя
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                telegram_username = request.POST.get("telegram_username", "").strip()
                if not telegram_username:
                    telegram_username = f"tg_{get_random_string(10)}"
                profile.telegram_username = telegram_username
                profile.save()
            else:
                messages.warning(request, "Профиль уже существует для данного пользователя.")

            login(request, user)  # Авторизуем пользователя после регистрации
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
            return JsonResponse({"success": False, "error": "Cart item not found."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@login_required
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

    return JsonResponse({"success": False, "error": "Invalid request method."})

@login_required
@csrf_exempt
def send_to_bot(request):
    if request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({"success": False, "error": "Пользователь не авторизован."})

            cart_items = CartItem.objects.filter(user=request.user)
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

            telegram_username = getattr(request.user.profile, 'telegram_username', None)
            if not telegram_username:
                return JsonResponse({"success": False, "error": "Telegram username не найден. Укажите его в профиле."})

            # ✅ Асинхронный вызов без `no running event loop`
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.create_task(send_order_notification(telegram_username, items, total_price))

            return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Ошибка при отправке заказа в бота: {e}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Некорректный метод запроса."})


def payment(request):
    return render(request, 'shop/payment.html')

@login_required
def profile(request):
    if request.method == "POST":
        telegram_username = request.POST.get("telegram_username", "").strip()
        if telegram_username:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.telegram_username = telegram_username
            profile.save()
            messages.success(request, "Telegram Username успешно обновлен!")
        else:
            messages.error(request, "Введите корректный Telegram Username.")
        return redirect("profile")

    return render(request, "shop/profile.html")
