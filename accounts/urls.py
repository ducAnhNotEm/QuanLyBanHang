from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    WalletView,
    TopUpRequestCreateView,
    TopUpRequestListView,
    TopUpRequestApproveView,
    TopUpRequestRejectView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/topup/create/', TopUpRequestCreateView.as_view(), name='topup_request_create'),
    path('wallet/topup/requests/', TopUpRequestListView.as_view(), name='topup_request_list'),
    path(
        'wallet/topup/requests/<int:id>/approve/',
        TopUpRequestApproveView.as_view(),
        name='topup_request_approve',
    ),
    path(
        'wallet/topup/requests/<int:id>/reject/',
        TopUpRequestRejectView.as_view(),
        name='topup_request_reject',
    ),
]
