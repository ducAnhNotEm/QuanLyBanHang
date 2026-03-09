from decimal import Decimal, InvalidOperation

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def product_image_upload_path(instance, filename):
    return f'products/images/{filename}'


class Product(models.Model):
    productName = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stockQuantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=product_image_upload_path, blank=True, null=True)

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
        # Backfill slug for legacy rows created before slug logic was fixed.
        if not self.slug and self.pk:
            self.slug = self._generate_unique_slug()
            Product.objects.filter(pk=self.pk).update(slug=self.slug)
        return reverse('product_detail', kwargs={'slug': self.slug})

    @property
    def formatted_price(self):
        try:
            amount = int(Decimal(self.price))
        except (TypeError, ValueError, InvalidOperation):
            return ''
        return f"{amount:,}".replace(',', '.') + " VND"

    def __str__(self):
        return self.productName
