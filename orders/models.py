from decimal import Decimal

from django.db import models

from accounts.models import Customer
from products.models import Product


class Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='cart')
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Gio hang cua {self.customer.fullName}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    isSelected = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product')
        ]

    @property
    def subTotal(self):
        return (self.product.price or Decimal('0')) * self.quantity

    def __str__(self):
        return f'{self.product.productName} x {self.quantity}'


class Order(models.Model):
    STATUS_CHOICES = [
        ('PAID', 'PAID'),
        ('CANCELLED', 'CANCELLED'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    totalAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PAID')
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Don hang #{self.id} - {self.customer.fullName}'


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_details')
    quantity = models.PositiveIntegerField(default=1)
    unitPrice = models.DecimalField(max_digits=12, decimal_places=2)
    subTotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'DH#{self.order_id} - {self.product.productName}'
