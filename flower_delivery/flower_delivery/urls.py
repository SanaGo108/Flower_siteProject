from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from shop import views
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart, name='cart'),
    path('cart/update/', views.update_cart, name='update_cart'),  # Добавлен маршрут для обновления корзины
    path('cart/add/', views.add_to_cart, name="add_to_cart"),
    path('cart/checkout/', views.checkout, name='checkout'),  # Добавить обработчик checkout
    path('accounts/', include('django.contrib.auth.urls')),  # Добавляем маршруты аутентификации
    path('accounts/register/', views.register, name='register'),  # Маршрут регистрации
    path('success/', views.success_page, name='success_page'),  # Добавьте этот маршрут
    path('bot/start/', lambda request: redirect('https://t.me/FlDel_bot')),
    path('payment/', views.payment, name='payment'),  # Новый маршрут для оплаты Ссылка на бота
]

# Маршруты для медиафайлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
