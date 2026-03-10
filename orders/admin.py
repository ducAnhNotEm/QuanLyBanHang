from django.contrib import admin

from .models import Cart, CartItem, Order, OrderDetail


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderDetail)
