import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from flower_delivery.bot import send_order_notification

from .models import Order, OrderItem, Flower, CartItem

def home(request):
    return render(request, 'shop/home.html')

def catalog(request):
    flowers = Flower.objects.all()
    return render(request, 'shop/catalog.html', {'flowers': flowers})

@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            flower_id = data.get("id")
            quantity = int(data.get("quantity", 1))

            flower = Flower.objects.get(id=flower_id)
            cart_item, created = CartItem.objects.get_or_create(flower=flower)
            cart_item.quantity += quantity if not created else quantity
            cart_item.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False})

@csrf_exempt
def update_cart(request):
    if request.method == "POST":
        try:
            # Проверяем, что тело запроса существует
            if not request.body:
                return JsonResponse({"success": False, "error": "Request body is empty."})

            # Попытка загрузить JSON из тела запроса
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                return JsonResponse({"success": False, "error": f"Invalid JSON: {str(e)}"})

            # Извлекаем данные из JSON
            flower_id = data.get("id")
            quantity = data.get("quantity")

            # Проверяем наличие и валидность параметров
            if flower_id is None or quantity is None:
                return JsonResponse({"success": False, "error": "Missing 'id' or 'quantity'."})

            try:
                quantity = int(quantity)
            except ValueError:
                return JsonResponse({"success": False, "error": "Invalid value for 'quantity'. Must be an integer."})

            # Обновляем или удаляем товар в корзине
            if quantity < 1:
                CartItem.objects.filter(flower_id=flower_id).delete()
            else:
                cart_item = CartItem.objects.get(flower_id=flower_id)
                cart_item.quantity = quantity
                cart_item.save()

            return JsonResponse({"success": True})
        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "Cart item not found."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method."})




def cart(request):
    cart_items = CartItem.objects.all()
    total_price = sum(item.quantity * item.flower.price for item in cart_items)
    return render(request, 'shop/cart.html', {"cart": cart_items, "cart_total": total_price})

@login_required
def checkout(request):
    if request.method == 'POST':
        try:
            telegram_username = request.POST.get('telegram_username', request.user.username)
            delivery_date = request.POST.get('delivery_date')
            delivery_time = request.POST.get('delivery_time')
            delivery_address = request.POST.get('delivery_address')
            comment = request.POST.get('comment', '')

            if not all([telegram_username, delivery_date, delivery_time, delivery_address]):
                return render(request, 'shop/checkout.html', {"error": "Заполните все обязательные поля."})

            order = Order.objects.create(
                user=request.user,
                telegram_username=telegram_username,
                delivery_date=delivery_date,
                delivery_time=delivery_time,
                delivery_address=delivery_address,
                comment=comment,
                total_price=0,
            )

            cart_items = CartItem.objects.all()
            total_price = sum(
                OrderItem.objects.create(order=order, flower=item.flower, quantity=item.quantity).flower.price * item.quantity
                for item in cart_items
            )
            cart_items.delete()
            order.total_price = total_price
            order.save()

            send_order_notification(order)

            return redirect('success_page')
        except Exception as e:
            return render(request, 'shop/checkout.html', {"error": str(e)})

    return render(request, 'shop/checkout.html')

def success_page(request):
    return render(request, 'shop/success_page.html')

def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'shop/register.html', {'form': form})

def payment(request):
    return render(request, 'shop/payment.html')
