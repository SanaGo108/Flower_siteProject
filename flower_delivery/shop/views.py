from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Flower, Order
from .forms import RegistrationForm
from django.contrib.auth.forms import UserCreationForm
import json

def home(request):
    return render(request, 'shop/home.html')

def catalog(request):
    flowers = Flower.objects.all()
    return render(request, 'shop/catalog.html', {'flowers': flowers})

@csrf_exempt
def add_to_cart(request):
    if request.method == "POST":
        data = json.loads(request.body)
        flower_id = data.get("id")
        quantity = data.get("quantity", 1)
        price = data.get("price")

        # Assuming cart is stored in session
        cart = request.session.get("cart", {})
        if flower_id in cart:
            cart[flower_id]["quantity"] += int(quantity)
        else:
            cart[flower_id] = {"quantity": int(quantity), "price": price}
        request.session["cart"] = cart
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})

def cart(request):
    cart = request.session.get("cart", {})
    flowers = Flower.objects.filter(id__in=cart.keys())
    cart_items = []
    total_price = 0
    for flower in flowers:
        quantity = cart[str(flower.id)]["quantity"]
        price = float(cart[str(flower.id)]["price"])
        total_price += quantity * price
        cart_items.append({
            "flower": flower,
            "quantity": quantity,
            "total": quantity * price
        })
    return render(request, "shop/cart.html", {"cart": cart_items, "cart_total": total_price})


@login_required
def cart(request):
    if request.method == 'POST':
        # Логика обработки заказа
        pass
    return render(request, 'shop/cart.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Перенаправление на страницу входа
    else:
        form = UserCreationForm()
    return render(request, 'shop/register.html', {'form': form})