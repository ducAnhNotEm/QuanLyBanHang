from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.models import Customer, Wallet
from products.models import Product
from .models import Cart, CartItem, Order, OrderDetail


def parse_quantity(value):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


def safe_next_url(value):
    if value and value.startswith('/'):
        return value
    return None


def to_vnd_integer(amount):
    rounded = amount.quantize(Decimal('1'))
    if rounded != amount:
        return None
    return int(rounded)


class CustomerRequiredMixin(LoginRequiredMixin):
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_staff:
            messages.error(request, 'Tài khoản admin không dùng chức năng mua hàng.')
            return redirect('home')

        try:
            request.customer_profile = request.user.customer_profile
        except Customer.DoesNotExist:
            messages.error(request, 'Không tìm thấy hồ sơ khách hàng.')
            return redirect('home')

        return super().dispatch(request, *args, **kwargs)


class CartView(CustomerRequiredMixin, View):
    template_name = 'orders/cart.html'

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(customer=request.customer_profile)
        items = cart.items.select_related('product').order_by('-id')
        selected_total = sum(
            (item.subTotal for item in items if item.isSelected),
            Decimal('0'),
        )

        return render(request, self.template_name, {
            'cart': cart,
            'items': items,
            'selected_total': selected_total,
        })


class AddToCartView(CustomerRequiredMixin, View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        quantity = parse_quantity(request.POST.get('quantity'))
        next_url = safe_next_url(request.POST.get('next'))

        def redirect_back():
            if next_url:
                return redirect(next_url)
            return redirect('product_detail', slug=product.slug)

        if quantity is None:
            messages.error(request, 'Số lượng không hợp lệ.')
            return redirect_back()

        if product.stockQuantity <= 0:
            messages.error(request, 'Sản phẩm đã hết hàng.')
            return redirect_back()

        if quantity > product.stockQuantity:
            messages.error(request, 'Số lượng vượt quá tồn kho hiện tại.')
            return redirect_back()

        cart, _ = Cart.objects.get_or_create(customer=request.customer_profile)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 0, 'isSelected': True},
        )

        new_quantity = quantity if created else item.quantity + quantity
        if new_quantity > product.stockQuantity:
            messages.error(request, 'Tổng số lượng trong giỏ vượt quá tồn kho.')
            return redirect_back()

        item.quantity = new_quantity
        item.isSelected = True
        item.save()

        messages.success(request, 'Đã thêm sản phẩm vào giỏ hàng.')
        if next_url:
            return redirect(next_url)
        return redirect('cart')


class CartItemSelectionToggleView(CustomerRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__customer=request.customer_profile,
        )
        item.isSelected = request.POST.get('is_selected') == '1'
        item.save(update_fields=['isSelected'])
        messages.success(request, 'Đã cập nhật lựa chọn sản phẩm.')
        return redirect('cart')


class CartItemUpdateView(CustomerRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(
            CartItem.objects.select_related('cart', 'product'),
            id=item_id,
            cart__customer=request.customer_profile,
        )
        quantity = parse_quantity(request.POST.get('quantity'))

        if quantity is None:
            messages.error(request, 'Số lượng không hợp lệ.')
            return redirect('cart')

        if quantity > item.product.stockQuantity:
            messages.error(request, 'Số lượng vượt quá tồn kho hiện tại.')
            return redirect('cart')

        item.quantity = quantity
        item.save(update_fields=['quantity'])
        messages.success(request, 'Đã cập nhật số lượng sản phẩm trong giỏ.')
        return redirect('cart')


class CartItemRemoveView(CustomerRequiredMixin, View):
    def post(self, request, item_id):
        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__customer=request.customer_profile,
        )
        item.delete()
        messages.success(request, 'Đã xóa sản phẩm khỏi giỏ.')
        return redirect('cart')


class BuyNowView(CustomerRequiredMixin, View):
    @transaction.atomic
    def post(self, request, product_id):
        product = get_object_or_404(Product.objects.select_for_update(), id=product_id)
        quantity = parse_quantity(request.POST.get('quantity'))

        if quantity is None:
            messages.error(request, 'Số lượng không hợp lệ.')
            return redirect('product_detail', slug=product.slug)

        if product.stockQuantity <= 0:
            messages.error(request, 'Sản phẩm đã hết hàng.')
            return redirect('product_detail', slug=product.slug)

        if quantity > product.stockQuantity:
            messages.error(request, 'Số lượng vượt quá tồn kho hiện tại.')
            return redirect('product_detail', slug=product.slug)

        total_amount = product.price * quantity
        total_amount_vnd = to_vnd_integer(total_amount)
        if total_amount_vnd is None:
            messages.error(request, 'Giá trị thanh toán không hợp lệ cho ví VNĐ.')
            return redirect('product_detail', slug=product.slug)

        try:
            wallet = Wallet.objects.select_for_update().get(customer=request.customer_profile)
        except Wallet.DoesNotExist:
            messages.error(request, 'Không tìm thấy ví để thanh toán.')
            return redirect('home')

        if wallet.balance < total_amount_vnd:
            messages.error(request, 'Số dư ví không đủ để thanh toán.')
            return redirect('product_detail', slug=product.slug)

        product.stockQuantity -= quantity
        product.save(update_fields=['stockQuantity'])

        order = Order.objects.create(
            customer=request.customer_profile,
            totalAmount=total_amount,
            status='PAID',
        )
        OrderDetail.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unitPrice=product.price,
            subTotal=total_amount,
        )

        wallet.balance -= total_amount_vnd
        wallet.save(update_fields=['balance'])

        messages.success(request, 'Mua hàng thành công.')
        return redirect('order_detail', id=order.id)


class CartCheckoutView(CustomerRequiredMixin, View):
    @transaction.atomic
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(customer=request.customer_profile)
        selected_items = list(
            cart.items
            .select_related('product')
            .filter(isSelected=True)
        )

        if not selected_items:
            messages.error(request, 'Hãy chọn ít nhất 1 sản phẩm trong giỏ để thanh toán.')
            return redirect('cart')

        product_ids = [item.product_id for item in selected_items]
        products = Product.objects.select_for_update().filter(id__in=product_ids)
        product_map = {product.id: product for product in products}

        for item in selected_items:
            product = product_map.get(item.product_id)
            if product is None or item.quantity > product.stockQuantity:
                messages.error(
                    request,
                    f'Sản phẩm "{item.product.productName}" không đủ tồn kho để thanh toán.',
                )
                return redirect('cart')

        total_amount = Decimal('0')
        for item in selected_items:
            product = product_map[item.product_id]
            total_amount += product.price * item.quantity

        total_amount_vnd = to_vnd_integer(total_amount)
        if total_amount_vnd is None:
            messages.error(request, 'Giá trị thanh toán không hợp lệ cho ví VNĐ.')
            return redirect('cart')

        try:
            wallet = Wallet.objects.select_for_update().get(customer=request.customer_profile)
        except Wallet.DoesNotExist:
            messages.error(request, 'Không tìm thấy ví để thanh toán.')
            return redirect('home')

        if wallet.balance < total_amount_vnd:
            messages.error(request, 'Số dư ví không đủ để thanh toán.')
            return redirect('cart')

        order = Order.objects.create(
            customer=request.customer_profile,
            totalAmount=0,
            status='PAID',
        )

        for item in selected_items:
            product = product_map[item.product_id]
            subtotal = product.price * item.quantity

            OrderDetail.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                unitPrice=product.price,
                subTotal=subtotal,
            )

            product.stockQuantity -= item.quantity
            product.save(update_fields=['stockQuantity'])

        order.totalAmount = total_amount
        order.save(update_fields=['totalAmount'])

        wallet.balance -= total_amount_vnd
        wallet.save(update_fields=['balance'])

        cart.items.filter(id__in=[item.id for item in selected_items]).delete()
        messages.success(request, 'Thanh toán thành công.')
        return redirect('order_detail', id=order.id)


class OrderDetailView(CustomerRequiredMixin, View):
    template_name = 'orders/order_detail.html'

    def get(self, request, id):
        order = get_object_or_404(
            Order.objects.select_related('customer').prefetch_related('details__product'),
            id=id,
            customer=request.customer_profile,
        )
        return render(request, self.template_name, {'order': order})


class OrderHistoryView(CustomerRequiredMixin, View):
    template_name = 'orders/order_history.html'

    def get(self, request):
        orders = (
            Order.objects
            .filter(customer=request.customer_profile)
            .prefetch_related('details__product')
            .order_by('-createdAt')
        )
        return render(request, self.template_name, {'orders': orders})
