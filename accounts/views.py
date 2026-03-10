import re

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View

from .forms import RegisterForm
from .models import Customer, Wallet, TopUpRequest


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


class WalletView(View):
    template_name = 'wallet/wallet.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff:
            return redirect('home')

        try:
            customer = request.user.customer_profile
            wallet = customer.wallet
        except Customer.DoesNotExist:
            messages.error(request, 'Không tìm thấy thông tin khách hàng.')
            return redirect('home')
        except Wallet.DoesNotExist:
            messages.error(request, 'Không tìm thấy ví tiền.')
            return redirect('home')

        return render(request, self.template_name, {
            'customer': customer,
            'wallet': wallet,
        })


class TopUpRequestCreateView(View):
    template_name = 'wallet/topup_request_create.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff:
            return redirect('home')

        return render(request, self.template_name)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff:
            return redirect('home')

        amount_input = (request.POST.get('amount') or '').strip()
        note = request.POST.get('note')

        if not re.fullmatch(r'[\d\s\.,]+', amount_input):
            messages.error(request, 'Số tiền không hợp lệ.')
            return render(request, self.template_name)

        amount_digits = re.sub(r'\D', '', amount_input)
        if not amount_digits:
            messages.error(request, 'Số tiền không hợp lệ.')
            return render(request, self.template_name)

        amount = int(amount_digits)

        if amount <= 0:
            messages.error(request, 'Số tiền nạp phải lớn hơn 0.')
            return render(request, self.template_name)

        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
            messages.error(request, 'Không tìm thấy thông tin khách hàng.')
            return redirect('home')

        TopUpRequest.objects.create(
            customer=customer,
            amount=amount,
            note=note,
            status='PENDING'
        )

        messages.success(request, 'Gửi yêu cầu nạp tiền thành công.')
        return redirect('wallet')


class TopUpRequestListView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'wallet/topup_request_list.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        requests = TopUpRequest.objects.all().order_by('-id')
        return render(request, self.template_name, {'requests': requests})


class TopUpRequestApproveView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    @transaction.atomic
    def post(self, request, id):
        topup_request = get_object_or_404(TopUpRequest, id=id)

        if topup_request.status != 'PENDING':
            messages.error(request, 'Yêu cầu này đã được xử lý trước đó.')
            return redirect('topup_request_list')

        wallet = topup_request.customer.wallet
        wallet.balance += topup_request.amount
        wallet.save()

        topup_request.status = 'APPROVED'
        topup_request.save()

        messages.success(request, 'Đã duyệt yêu cầu nạp tiền và cộng tiền vào ví.')
        return redirect('topup_request_list')


class TopUpRequestRejectView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, id):
        topup_request = get_object_or_404(TopUpRequest, id=id)

        if topup_request.status != 'PENDING':
            messages.error(request, 'Yêu cầu này đã được xử lý trước đó.')
            return redirect('topup_request_list')

        topup_request.status = 'REJECTED'
        topup_request.save()

        messages.success(request, 'Đã từ chối yêu cầu nạp tiền.')
        return redirect('topup_request_list')
