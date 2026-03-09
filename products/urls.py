from django.urls import path
from .views import (
    HomeView,
    ProductListView,
    ProductCreateView,
    ProductDetailView,
    ProductUpdateView,
    ProductDeleteView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/update/<int:id>/', ProductUpdateView.as_view(), name='product_update'),
    path('products/delete/<int:id>/', ProductDeleteView.as_view(), name='product_delete'),
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
]