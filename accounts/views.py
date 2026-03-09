from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import transaction

from .forms import RegisterForm
from .models import Customer, Wallet


class RegisterView(View):
    template_name = 'trangChu/register.html'

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {'form': form})

    @transaction.atomic
    def post(self, request):
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            customer = Customer.objects.create(
                user=user,
                fullName=form.cleaned_data['fullName'],
                phoneNumber=form.cleaned_data['phoneNumber'],
                address=form.cleaned_data['address'],
                dateOfBirth=form.cleaned_data['dateOfBirth'],
                gender=form.cleaned_data['gender']
            )

            Wallet.objects.create(
                customer=customer,
                balance=0
            )

            messages.success(request, 'Đăng ký thành công. Hãy đăng nhập.')
            return redirect('login')

        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = 'trangChu/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')

        messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu.')
        return render(request, self.template_name)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')
