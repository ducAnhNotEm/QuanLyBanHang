from django.urls import path

from .views import (
    AddToCartView,
    BuyNowView,
    CartCheckoutView,
    CartItemRemoveView,
    CartItemSelectionToggleView,
    CartItemUpdateView,
    CartView,
    DiscountCodeListView,
    DiscountCodeToggleView,
    OrderDetailView,
    OrderHistoryView,
)


urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/<int:product_id>/', AddToCartView.as_view(), name='cart_add'),
    path('cart/item/<int:item_id>/update/', CartItemUpdateView.as_view(), name='cart_item_update'),
    path('cart/item/<int:item_id>/remove/', CartItemRemoveView.as_view(), name='cart_item_remove'),
    path('cart/item/<int:item_id>/select/', CartItemSelectionToggleView.as_view(), name='cart_item_select'),
    path('cart/checkout/', CartCheckoutView.as_view(), name='cart_checkout'),
    path('buy-now/<int:product_id>/', BuyNowView.as_view(), name='buy_now'),
    path('discount-codes/', DiscountCodeListView.as_view(), name='discount_code_list'),
    path('discount-codes/<int:id>/toggle/', DiscountCodeToggleView.as_view(), name='discount_code_toggle'),
    path('orders/<int:id>/', OrderDetailView.as_view(), name='order_detail'),
    path('orders/history/', OrderHistoryView.as_view(), name='order_history'),
]
