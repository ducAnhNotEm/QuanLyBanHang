from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def product_image_upload_path(instance, filename):
    return f'products/images/{filename}'


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('banh-keo', 'Bánh kẹo'),
        ('nuoc-uong', 'Nước uống'),
        ('thuc-pham', 'Thực phẩm'),
        ('do-kho', 'Đồ khô'),
        ('do-hop', 'Đồ hộp'),
        ('quan-ao', 'Quần áo'),
        ('giay-dep', 'Giày dép'),
        ('phu-kien', 'Phụ kiện'),
        ('do-gia-dung', 'Đồ gia dụng'),
        ('my-pham', 'Mỹ phẩm'),
        ('do-dien-tu', 'Đồ điện tử'),
    ]

    productName = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='thuc-pham'
    )
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discountPercent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    stockQuantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=product_image_upload_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.productName

    def _generate_unique_slug(self):
        base_slug = slugify(self.productName) or 'product'
        slug = base_slug
        counter = 1

        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    @property
    def formatted_price(self):
        try:
            amount = int(Decimal(self.price).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        except (TypeError, ValueError, InvalidOperation):
            return ''
        return f"{amount:,}".replace(',', '.') + " VND"

    @property
    def clamped_discount_percent(self):
        try:
            discount = Decimal(self.discountPercent or 0)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal('0')
        return max(Decimal('0'), min(Decimal('100'), discount))

    @property
    def discounted_price(self):
        try:
            price = Decimal(self.price or 0)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal('0')
        discounted = price * (Decimal('100') - self.clamped_discount_percent) / Decimal('100')
        return discounted.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

    @property
    def formatted_discounted_price(self):
        try:
            amount = int(Decimal(self.discounted_price).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        except (TypeError, ValueError, InvalidOperation):
            return ''
        return f"{amount:,}".replace(',', '.') + " VND"
