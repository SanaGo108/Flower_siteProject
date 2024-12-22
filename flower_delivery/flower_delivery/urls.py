from django.contrib import admin
from django.urls import path, include
from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart, name='cart'),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path('accounts/', include('django.contrib.auth.urls')),  # Добавляем маршруты аутентификации
    path('accounts/register/', views.register, name='register'),  # Маршрут регистрации
]
