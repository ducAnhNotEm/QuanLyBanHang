from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Case, When, Value, IntegerField
from django.urls import reverse
from django.utils.text import slugify
import re

from .models import Product


def ensure_product_slugs():
    missing_slug_products = Product.objects.filter(Q(slug__isnull=True) | Q(slug=''))
    for product in missing_slug_products:
        product.slug = ''
        product.save(update_fields=['slug'])


def extract_search_tokens(keyword):
    raw_tokens = re.findall(r'\w+', keyword.lower(), flags=re.UNICODE)
    tokens = []
    seen = set()

    for token in raw_tokens:
        if len(token) < 2:
            continue

        token_variants = [token, slugify(token)]
        for variant in token_variants:
            if variant and variant not in seen:
                seen.add(variant)
                tokens.append(variant)

    return tokens


def search_products(queryset, keyword):
    keyword = (keyword or '').strip()
    if not keyword:
        return queryset.order_by('-id')

    tokens = extract_search_tokens(keyword)
    slug_keyword = slugify(keyword)

    combined_filter = Q(productName__icontains=keyword) | Q(description__icontains=keyword)
    relevance_score = (
        Case(
            When(productName__icontains=keyword, then=Value(8)),
            default=Value(0),
            output_field=IntegerField(),
        )
        + Case(
            When(description__icontains=keyword, then=Value(5)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )

    if slug_keyword:
        combined_filter |= Q(slug__icontains=slug_keyword)
        relevance_score += Case(
            When(slug__icontains=slug_keyword, then=Value(5)),
            default=Value(0),
            output_field=IntegerField(),
        )

    for token in tokens:
        combined_filter |= (
            Q(productName__icontains=token)
            | Q(description__icontains=token)
            | Q(slug__icontains=token)
        )
        relevance_score += (
            Case(
                When(productName__icontains=token, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            )
            + Case(
                When(description__icontains=token, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            )
            + Case(
                When(slug__icontains=token, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )

    return (
        queryset
        .filter(combined_filter)
        .annotate(search_rank=relevance_score)
        .order_by('-search_rank', '-id')
    )


class HomeView(View):
    template_name = 'products/home.html'

    def get(self, request):
        ensure_product_slugs()
        keyword = request.GET.get('q', '').strip()

        products = search_products(Product.objects.all(), keyword)

        canonical_home_url = request.build_absolute_uri(reverse('home'))
        if keyword:
            meta_title = f'Kết quả tìm kiếm "{keyword}" | Sales Management'
            meta_description = (
                f'Kết quả tìm kiếm sản phẩm theo từ khóa "{keyword}" '
                'trong hệ thống quản lý bán hàng Sales Management.'
            )
            robots_content = 'noindex, follow'
        else:
            meta_title = 'Trang chủ quản lý bán hàng | Tìm kiếm sản phẩm nhanh'
            meta_description = (
                'Trang chủ hệ thống quản lý bán hàng bằng Django, hiển thị sản phẩm mới nhất, '
                'tìm kiếm sản phẩm nhanh và hỗ trợ quản lý bán hàng hiệu quả.'
            )
            robots_content = 'index, follow'

        return render(request, self.template_name, {
            'products': products,
            'keyword': keyword,
            'meta_title': meta_title,
            'meta_description': meta_description,
            'robots_content': robots_content,
            'canonical_url': canonical_home_url,
            'canonical_home_url': canonical_home_url,
        })


class ProductListView(LoginRequiredMixin, View):
    template_name = 'products/product_list.html'
    login_url = 'login'

    def get(self, request):
        ensure_product_slugs()
        keyword = request.GET.get('q', '').strip()
        products = search_products(Product.objects.all(), keyword)
        return render(request, self.template_name, {
            'products': products,
            'keyword': keyword,
        })


class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/product_create.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        productName = request.POST.get('productName')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stockQuantity = request.POST.get('stockQuantity')
        image = request.FILES.get('image')

        if productName and price and stockQuantity:
            Product.objects.create(
                productName=productName,
                description=description,
                price=price,
                stockQuantity=stockQuantity,
                image=image
            )
            return redirect('product_list')

        return render(request, self.template_name, {
            'error': 'Vui lòng nhập đầy đủ tên sản phẩm, giá và số lượng tồn.'
        })


class ProductDetailView(View):
    template_name = 'products/product_detail.html'

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        related_products = Product.objects.exclude(id=product.id).order_by('-id')[:4]
        canonical_url = request.build_absolute_uri(product.get_absolute_url())
        meta_description = (
            (product.description or f'Chi tiết sản phẩm {product.productName}')
        )[:150]
        product_image_url = request.build_absolute_uri(product.image.url) if product.image else ''

        return render(request, self.template_name, {
            'product': product,
            'related_products': related_products,
            'canonical_url': canonical_url,
            'meta_description': meta_description,
            'product_image_url': product_image_url,
        })


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/product_update.html'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, id):
        product = get_object_or_404(Product, id=id)
        return render(request, self.template_name, {'product': product})

    def post(self, request, id):
        product = get_object_or_404(Product, id=id)

        product.productName = request.POST.get('productName')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stockQuantity = request.POST.get('stockQuantity')

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
