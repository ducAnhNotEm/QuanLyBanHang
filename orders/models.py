from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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
        base_subtotal = (Decimal(self.product.price or 0) * self.quantity).quantize(
            Decimal('1'),
            rounding=ROUND_HALF_UP,
        )
        discount_amount = (
            Decimal(self.product.price or 0)
            * self.quantity
            * Decimal(self.product.clamped_discount_percent or 0)
            / Decimal('100')
        ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        total = base_subtotal - discount_amount
        return max(Decimal('0'), total)

    @property
    def discountAmount(self):
        full_price_subtotal = (Decimal(self.product.price or 0) * self.quantity).quantize(
            Decimal('1'),
            rounding=ROUND_HALF_UP,
        )
        return full_price_subtotal - self.subTotal

    def __str__(self):
        return f'{self.product.productName} x {self.quantity}'


class DiscountCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discountPercent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    isActive = models.BooleanField(default=True)
    validFrom = models.DateTimeField(blank=True, null=True)
    validTo = models.DateTimeField(blank=True, null=True)
    usageLimit = models.PositiveIntegerField(blank=True, null=True)
    usedCount = models.PositiveIntegerField(default=0)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-createdAt']

    def clean(self):
        if self.validFrom and self.validTo and self.validFrom > self.validTo:
            raise ValidationError({'validTo': 'Thời gian kết thúc phải sau thời gian bắt đầu.'})

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} ({self.discountPercent}%)'


class Order(models.Model):
    STATUS_CHOICES = [
        ('PAID', 'PAID'),
        ('CANCELLED', 'CANCELLED'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    subTotalAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discountAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    couponCode = models.CharField(max_length=50, blank=True, default='')
    couponDiscountAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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
    discountPercent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discountAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subTotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'DH#{self.order_id} - {self.product.productName}'
