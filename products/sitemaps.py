from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Product


class StaticViewSitemap(Sitemap):
    changefreq = 'daily'
    priority = 1.0

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Product.objects.exclude(slug__isnull=True).exclude(slug='').order_by('-id')
