from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'trangChu/index.html')
def login_view(request):
    return render(request, 'trangChu/login.html')
def register_view(request):
    return render(request, 'trangChu/register.html')