from django.contrib import admin

from .models import Cart, CartItem, DiscountCode, Order, OrderDetail


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderDetail)


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discountPercent',
        'isActive',
        'validFrom',
        'validTo',
        'usageLimit',
        'usedCount',
    )
    list_filter = ('isActive',)
    search_fields = ('code',)
    readonly_fields = ('usedCount', 'createdAt')
