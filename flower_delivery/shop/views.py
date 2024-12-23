import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from flower_delivery.bot import send_order_notification  # Абсолютный импорт

from .models import Order, OrderItem, Flower, CartItem


# Главная страница
def home(request):
    return render(request, 'shop/home.html')


# Каталог товаров
def catalog(request):
    flowers = Flower.objects.all()
    return render(request, 'shop/catalog.html', {'flowers': flowers})


# Добавление товара в корзину
@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            flower_id = data.get("id")
            quantity = int(data.get("quantity", 1))

            flower = Flower.objects.get(id=flower_id)
            cart_item, created = CartItem.objects.get_or_create(flower=flower)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False})


# Просмотр корзины
def cart(request):
    cart_items = CartItem.objects.all()
    total_price = sum(item.quantity * item.flower.price for item in cart_items)
    return render(request, 'shop/cart.html', {"cart": cart_items, "cart_total": total_price})


# Оформление заказа
@login_required
def checkout(request):
    if request.method == 'POST':
        try:
            # Получение данных из формы
            telegram_username = request.POST.get('telegram_username') or request.user.username
            delivery_date = request.POST.get('delivery_date')
            delivery_time = request.POST.get('delivery_time')
            delivery_address = request.POST.get('delivery_address')
            comment = request.POST.get('comment', '')

            # Проверка наличия данных
            if not telegram_username or not delivery_date or not delivery_time or not delivery_address:
                return render(request, 'shop/checkout.html', {
                    "error": "Заполните все обязательные поля."
                })

            # Создание заказа
            order = Order.objects.create(
                user=request.user,
                telegram_username=telegram_username,
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                delivery_address=delivery_address,
                comment=comment,
                total_price=0  # Рассчитаем позже
            )

            # Перенос товаров из корзины в заказ
            cart_items = CartItem.objects.all()
            total_price = 0
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    flower=item.flower,
                    quantity=item.quantity
                )
                total_price += item.quantity * item.flower.price
                item.delete()  # Удаление товара из корзины

            # Обновление общей цены заказа
            order.total_price = total_price
            order.save()

            # Отправка уведомления в Telegram
            send_order_notification(order)

            return redirect('success_page')  # Переход на страницу успешного оформления

        except Exception as e:
            return render(request, 'shop/checkout.html', {"error": str(e)})

    return render(request, 'shop/checkout.html')


# Страница успешного оформления
def success_page(request):
    return render(request, 'shop/success_page.html')


# Регистрация пользователя
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'shop/register.html', {'form': form})


# Страница оплаты
def payment(request):
    """
    Отображает страницу оплаты.
    """
    return render(request, 'shop/payment.html')
