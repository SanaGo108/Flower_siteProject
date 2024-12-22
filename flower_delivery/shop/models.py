from django.db import models
from django.contrib.auth.models import User

class Flower(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='flowers/')
    stock = models.PositiveIntegerField(default=0)  # Добавьте default=0, если оно отсутствует

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flowers = models.ManyToManyField(Flower, through='OrderItem')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    delivery_address = models.TextField()
    comment = models.TextField(blank=True, null=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    flower = models.ForeignKey(Flower, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
