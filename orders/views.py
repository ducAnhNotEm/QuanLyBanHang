from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import Customer, Wallet
from products.models import Product
from .models import Cart, CartItem, DiscountCode, Order, OrderDetail


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
    rounded = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    if rounded != amount:
        return None
    return int(rounded)


def calculate_line_amounts(product, quantity):
    unit_price = Decimal(product.price or 0)
    line_subtotal = unit_price * Decimal(quantity)
    discount_percent = Decimal(product.clamped_discount_percent or 0)
    line_discount = (line_subtotal * discount_percent / Decimal('100')).quantize(
        Decimal('1'),
        rounding=ROUND_HALF_UP,
    )
    line_subtotal = line_subtotal.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    line_total = line_subtotal - line_discount
    if line_total < 0:
        line_total = Decimal('0')
    return {
        'subtotal': line_subtotal,
        'discount_percent': discount_percent,
        'discount_amount': line_discount,
        'total': line_total,
    }


def normalize_discount_code(raw_code):
    return (raw_code or '').strip().upper()


def get_valid_discount_code(raw_code):
    normalized_code = normalize_discount_code(raw_code)
    if not normalized_code:
        return None, None

    try:
        discount_code = DiscountCode.objects.select_for_update().get(code=normalized_code)
    except DiscountCode.DoesNotExist:
        return None, 'Mã giảm giá không tồn tại.'

    now = timezone.now()
    if not discount_code.isActive:
        return None, 'Mã giảm giá đã bị vô hiệu hóa.'
    if discount_code.validFrom and now < discount_code.validFrom:
        return None, 'Mã giảm giá chưa đến thời gian áp dụng.'
    if discount_code.validTo and now > discount_code.validTo:
        return None, 'Mã giảm giá đã hết hạn.'
    if discount_code.usageLimit is not None and discount_code.usedCount >= discount_code.usageLimit:
        return None, 'Mã giảm giá đã hết lượt sử dụng.'

    return discount_code, None


def calculate_coupon_discount(total_amount, discount_code):
    if discount_code is None:
        return Decimal('0')

    coupon_discount = (
        total_amount * Decimal(discount_code.discountPercent or 0) / Decimal('100')
    ).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    if coupon_discount < 0:
        return Decimal('0')
    if coupon_discount > total_amount:
        return total_amount
    return coupon_discount


def parse_discount_percent(value):
    raw_value = (value or '').strip()
    try:
        discount_percent = Decimal(raw_value)
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Phần trăm giảm giá không hợp lệ.'
    if discount_percent < Decimal('0') or discount_percent > Decimal('100'):
        return None, 'Phần trăm giảm giá phải nằm trong khoảng 0-100.'
    return discount_percent, None


def parse_datetime_local(value):
    raw_value = (value or '').strip()
    if raw_value == '':
        return None, None
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None, 'Thời gian không hợp lệ.'
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed, None


def parse_usage_limit(value):
    raw_value = (value or '').strip()
    if raw_value == '':
        return None, None
    try:
        usage_limit = int(raw_value)
    except (TypeError, ValueError):
        return None, 'Giới hạn lượt dùng không hợp lệ.'
    if usage_limit <= 0:
        return None, 'Giới hạn lượt dùng phải lớn hơn 0.'
    return usage_limit, None


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


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Bạn không có quyền truy cập chức năng này.')
        return redirect('home')


class CartView(CustomerRequiredMixin, View):
    template_name = 'orders/cart.html'

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(customer=request.customer_profile)
        try:
            wallet_balance = request.customer_profile.wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0
        items = list(cart.items.select_related('product').order_by('-id'))
        selected_subtotal = Decimal('0')
        selected_discount = Decimal('0')
        selected_total = Decimal('0')

        for item in items:
            line_amounts = calculate_line_amounts(item.product, item.quantity)
            item.display_subtotal = line_amounts['subtotal']
            item.display_discount = line_amounts['discount_amount']
            item.display_total = line_amounts['total']
            if item.isSelected:
                selected_subtotal += line_amounts['subtotal']
                selected_discount += line_amounts['discount_amount']
                selected_total += line_amounts['total']

        return render(request, self.template_name, {
            'cart': cart,
            'items': items,
            'wallet_balance': wallet_balance,
            'selected_subtotal': selected_subtotal,
            'selected_discount': selected_discount,
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

        discount_code, discount_error = get_valid_discount_code(request.POST.get('discount_code'))
        if discount_error:
            messages.error(request, discount_error)
            return redirect('product_detail', slug=product.slug)

        line_amounts = calculate_line_amounts(product, quantity)
        subtotal_amount = line_amounts['subtotal']
        product_discount_amount = line_amounts['discount_amount']
        line_total_amount = line_amounts['total']
        coupon_discount_amount = calculate_coupon_discount(line_total_amount, discount_code)
        total_discount_amount = product_discount_amount + coupon_discount_amount
        total_amount = line_total_amount - coupon_discount_amount

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
            subTotalAmount=subtotal_amount,
            discountAmount=total_discount_amount,
            couponCode=discount_code.code if discount_code else '',
            couponDiscountAmount=coupon_discount_amount,
            totalAmount=total_amount,
            status='PAID',
        )
        OrderDetail.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unitPrice=product.price,
            discountPercent=line_amounts['discount_percent'],
            discountAmount=product_discount_amount,
            subTotal=line_total_amount,
        )

        wallet.balance -= total_amount_vnd
        wallet.save(update_fields=['balance'])
        if discount_code:
            discount_code.usedCount += 1
            discount_code.save(update_fields=['usedCount'])

        if discount_code:
            messages.success(request, f'Mua hàng thành công. Đã áp dụng mã {discount_code.code}.')
        else:
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

        subtotal_amount = Decimal('0')
        discount_amount = Decimal('0')
        total_amount = Decimal('0')
        line_amounts_by_item_id = {}

        for item in selected_items:
            product = product_map[item.product_id]
            line_amounts = calculate_line_amounts(product, item.quantity)
            line_amounts_by_item_id[item.id] = line_amounts
            subtotal_amount += line_amounts['subtotal']
            discount_amount += line_amounts['discount_amount']
            total_amount += line_amounts['total']

        discount_code, discount_error = get_valid_discount_code(request.POST.get('discount_code'))
        if discount_error:
            messages.error(request, discount_error)
            return redirect('cart')

        coupon_discount_amount = calculate_coupon_discount(total_amount, discount_code)
        total_discount_amount = discount_amount + coupon_discount_amount
        final_total_amount = total_amount - coupon_discount_amount

        total_amount_vnd = to_vnd_integer(final_total_amount)
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
            subTotalAmount=subtotal_amount,
            discountAmount=total_discount_amount,
            couponCode=discount_code.code if discount_code else '',
            couponDiscountAmount=coupon_discount_amount,
            totalAmount=final_total_amount,
            status='PAID',
        )

        for item in selected_items:
            product = product_map[item.product_id]
            line_amounts = line_amounts_by_item_id[item.id]

            OrderDetail.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                unitPrice=product.price,
                discountPercent=line_amounts['discount_percent'],
                discountAmount=line_amounts['discount_amount'],
                subTotal=line_amounts['total'],
            )

            product.stockQuantity -= item.quantity
            product.save(update_fields=['stockQuantity'])

        wallet.balance -= total_amount_vnd
        wallet.save(update_fields=['balance'])
        if discount_code:
            discount_code.usedCount += 1
            discount_code.save(update_fields=['usedCount'])

        cart.items.filter(id__in=[item.id for item in selected_items]).delete()
        if discount_code:
            messages.success(request, f'Thanh toán thành công. Đã áp dụng mã {discount_code.code}.')
        else:
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
        try:
            wallet_balance = request.customer_profile.wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0
        product_discount_amount = order.discountAmount - order.couponDiscountAmount
        if product_discount_amount < 0:
            product_discount_amount = Decimal('0')
        return render(request, self.template_name, {
            'order': order,
            'wallet_balance': wallet_balance,
            'product_discount_amount': product_discount_amount,
        })


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


class DiscountCodeListView(StaffRequiredMixin, View):
    template_name = 'orders/discount_code_list.html'

    def get(self, request):
        codes = DiscountCode.objects.all().order_by('-createdAt')
        return render(request, self.template_name, {'codes': codes})

    def post(self, request):
        code = normalize_discount_code(request.POST.get('code'))
        discount_percent, discount_percent_error = parse_discount_percent(request.POST.get('discount_percent'))
        valid_from, valid_from_error = parse_datetime_local(request.POST.get('valid_from'))
        valid_to, valid_to_error = parse_datetime_local(request.POST.get('valid_to'))
        usage_limit, usage_limit_error = parse_usage_limit(request.POST.get('usage_limit'))
        is_active = request.POST.get('is_active') == '1'

        validation_error = (
            ('Mã giảm giá không được để trống.' if code == '' else None)
            or discount_percent_error
            or valid_from_error
            or valid_to_error
            or usage_limit_error
        )
        if validation_error:
            messages.error(request, validation_error)
            codes = DiscountCode.objects.all().order_by('-createdAt')
            return render(request, self.template_name, {'codes': codes})

        if valid_from and valid_to and valid_from > valid_to:
            messages.error(request, 'Thời gian bắt đầu phải nhỏ hơn hoặc bằng thời gian kết thúc.')
            codes = DiscountCode.objects.all().order_by('-createdAt')
            return render(request, self.template_name, {'codes': codes})

        try:
            DiscountCode.objects.create(
                code=code,
                discountPercent=discount_percent,
                isActive=is_active,
                validFrom=valid_from,
                validTo=valid_to,
                usageLimit=usage_limit,
            )
        except IntegrityError:
            messages.error(request, 'Mã giảm giá đã tồn tại.')
            codes = DiscountCode.objects.all().order_by('-createdAt')
            return render(request, self.template_name, {'codes': codes})

        messages.success(request, f'Đã tạo mã giảm giá {code}.')
        return redirect('discount_code_list')


class DiscountCodeToggleView(StaffRequiredMixin, View):
    def post(self, request, id):
        discount_code = get_object_or_404(DiscountCode, id=id)
        discount_code.isActive = not discount_code.isActive
        discount_code.save(update_fields=['isActive'])
        if discount_code.isActive:
            messages.success(request, f'Đã bật mã {discount_code.code}.')
        else:
            messages.success(request, f'Đã tắt mã {discount_code.code}.')
        return redirect('discount_code_list')
