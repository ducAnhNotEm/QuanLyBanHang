from django.contrib import admin
from .models import Role, Customer, Wallet, TopUpRequest
# Register your models here.
admin.site.register(Role)
admin.site.register(Customer)
admin.site.register(Wallet)
admin.site.register(TopUpRequest)