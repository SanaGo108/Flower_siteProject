from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Flower(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='flowers/')
    stock = models.PositiveIntegerField(default=0)  # Количество на складе

    def __str__(self):
        return self.name


class CartItem(models.Model):
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def total_price(self):
        return self.quantity * self.flower.price

    def __str__(self):
        return f"{self.quantity} x {self.flower.name}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    telegram_username = models.CharField(max_length=255, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    delivery_address = models.TextField()
    comment = models.TextField(blank=True, null=True)

    def calculate_total_price(self):
        return sum(item.total_price() for item in self.orderitem_set.all())

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.calculate_total_price()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def total_price(self):
        return self.quantity * self.flower.price

    def __str__(self):
        return f"{self.quantity} x {self.flower.name} (Order {self.order.id})"

# Модель Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_username = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

# Сигнал для создания или обновления профиля
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Создаём профиль, если он отсутствует
        Profile.objects.get_or_create(user=instance)
    instance.profile.save()
