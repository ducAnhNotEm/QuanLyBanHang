from django import forms
from django.contrib.auth.models import User
from .models import Customer

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    fullName = forms.CharField(max_length=100)
    phoneNumber = forms.CharField(max_length=20)
    address = forms.CharField(required=False)
    dateOfBirth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(
        choices=Customer.GENDER_CHOICES,
        widget=forms.RadioSelect,
        initial='Nam'
    )
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Tên đăng nhập đã tồn tại.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email đã tồn tại.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Mật khẩu xác nhận không khớp.')

        return cleaned_data