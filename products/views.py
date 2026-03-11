from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from .models import Product


def ensure_product_slugs():
    products = Product.objects.filter(slug='')
    for product in products:
        product.slug = product._generate_unique_slug()
        product.save()


def search_products(queryset, keyword):
    if keyword:
        queryset = queryset.filter(
            Q(productName__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(category__icontains=keyword)
        )
    return queryset


class HomeView(View):
    template_name = 'products/home.html'

    def get(self, request):
        ensure_product_slugs()

        keyword = request.GET.get('q', '').strip()
        category = request.GET.get('category', '').strip()

        products = Product.objects.all().order_by('-id')
        products = search_products(products, keyword)

        if category:
            products = products.filter(category=category)

        slider_products = Product.objects.all().order_by('-id')[:3]
        aside_products = Product.objects.all().order_by('-id')[:5]
        categories = Product.CATEGORY_CHOICES

        return render(request, self.template_name, {
            'products': products,
            'slider_products': slider_products,
            'aside_products': aside_products,
            'categories': categories,
            'selected_category': category,
            'keyword': keyword,
            'meta_title': 'Trang chủ',
            'meta_description': 'Trang chủ hiển thị sản phẩm và danh mục sản phẩm',
            'robots_content': 'index, follow',
            'canonical_url': request.build_absolute_uri(reverse('home')),
        })


class ProductListView(View):
    template_name = 'products/product_list.html'

    def get(self, request):
        keyword = request.GET.get('q', '').strip()
        products = Product.objects.all().order_by('-id')
        products = search_products(products, keyword)

        return render(request, self.template_name, {
            'products': products,
            'keyword': keyword,
        })


class ProductDetailView(View):
    template_name = 'products/product_detail.html'

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
        canonical_url = request.build_absolute_uri(product.get_absolute_url())
        description_text = (product.description or '').strip()
        meta_description = description_text[:160] if description_text else f'Chi tiết sản phẩm {product.productName}'
        product_image_url = request.build_absolute_uri(product.image.url) if product.image else ''

        return render(request, self.template_name, {
            'product': product,
            'related_products': related_products,
            'canonical_url': canonical_url,
            'meta_description': meta_description,
            'product_image_url': product_image_url,
        })


class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/product_create.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        return render(request, self.template_name, {
            'categories': Product.CATEGORY_CHOICES
        })

    def post(self, request):
        productName = request.POST.get('productName', '').strip()
        category = request.POST.get('category', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        stockQuantity = request.POST.get('stockQuantity', '').strip()
        image = request.FILES.get('image')

        if not productName or not category or not price or not stockQuantity:
            return render(request, self.template_name, {
                'categories': Product.CATEGORY_CHOICES,
                'error': 'Vui lòng nhập đầy đủ thông tin.'
            })

        Product.objects.create(
            productName=productName,
            category=category,
            description=description,
            price=price,
            stockQuantity=stockQuantity,
            image=image
        )
        return redirect('product_list')


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/product_update.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, id):
        product = get_object_or_404(Product, id=id)
        return render(request, self.template_name, {
            'product': product,
            'categories': Product.CATEGORY_CHOICES,
        })

    def post(self, request, id):
        product = get_object_or_404(Product, id=id)

        product.productName = request.POST.get('productName', '').strip()
        product.category = request.POST.get('category', '').strip()
        product.description = request.POST.get('description', '').strip()
        product.price = request.POST.get('price', '').strip()
        product.stockQuantity = request.POST.get('stockQuantity', '').strip()

        image = request.FILES.get('image')
        if image:
            product.image = image

        product.slug = ''
        product.save()

        return redirect('product_list')


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/product_delete.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, id):
        product = get_object_or_404(Product, id=id)
        return render(request, self.template_name, {'product': product})

    def post(self, request, id):
        product = get_object_or_404(Product, id=id)
        product.delete()
        return redirect('product_list')
