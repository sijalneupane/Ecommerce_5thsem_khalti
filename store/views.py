from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
import uuid

from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import ProductForm, SearchForm, SignupForm, CheckoutForm

from django.contrib.auth import authenticate, login, logout
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('store:login')
    else:
        form = SignupForm()
    return render(request, 'store/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff or user.is_superuser:
                return redirect('store:admin_product_list')
            else:
                return redirect('store:product_list')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'store/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('store:product_list')
def product_list(request):
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    search_form = SearchForm()
    
    # Search functionality
    if request.GET.get('query'):
        query = request.GET.get('query')
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        search_form = SearchForm(initial={'query': query})
    
    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_form': search_form
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    return render(request, 'store/product_detail.html', {'product': product})

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'count': cart.get_total_items(),
            'message': f'{product.name} added to cart'
        })
    
    messages.success(request, f'{product.name} added to cart')
    return redirect('store:product_detail', slug=product.slug)

def cart_detail(request):
    cart = get_or_create_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

def cart_count(request):
    cart = get_or_create_cart(request)
    count = cart.get_total_items() if cart else 0
    return JsonResponse({'count': count})

@require_POST
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Cart updated successfully')
    else:
        cart_item.delete()
        messages.success(request, 'Item removed from cart')
    
    return redirect('store:cart_detail')

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart')
    return redirect('store:cart_detail')

# Admin views
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_product_list(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'store/admin/product_list.html', {'products': products})

@login_required
@user_passes_test(is_admin)
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully')
            return redirect('store:admin_product_list')
    else:
        form = ProductForm()
    return render(request, 'store/admin/product_form.html', {'form': form, 'title': 'Create Product'})

@login_required
@user_passes_test(is_admin)
def admin_product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully')
            return redirect('store:admin_product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/admin/product_form.html', {'form': form, 'title': 'Update Product'})

@login_required
@user_passes_test(is_admin)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully')
        return redirect('store:admin_product_list')
    return render(request, 'store/admin/product_confirm_delete.html', {'product': product})

# Checkout and Payment Views
def checkout(request):
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty')
        return redirect('store:cart_detail')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total_amount = cart.get_total_price()
            order.save()
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
            
            # Store order_id in session for payment processing
            request.session['order_id'] = str(order.order_id)
            
            return redirect('store:payment', order_id=order.order_id)
    else:
        form = CheckoutForm(user=request.user)
    
    context = {
        'form': form,
        'cart': cart,
    }
    return render(request, 'store/checkout.html', context)

def payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    # Khalti configuration (test environment)
    khalti_config = {
        'public_key': 'test_public_key_dc74e0fd57cb46cd93832aee0a390234',  # Correct test public key
        'secret_key': 'test_secret_key_f59e8b7d18b4499bb4af332897a8f2dc',  # Correct test secret key
        'test_mode': True
    }
    
    context = {
        'order': order,
        'khalti_config': khalti_config,
        'amount_in_paisa': int(order.total_amount * 100),  # Khalti expects amount in paisa
    }
    return render(request, 'store/payment.html', context)

@csrf_exempt
def khalti_verify(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'})
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        amount = data.get('amount')
        order_id = request.session.get('order_id')
        
        if not order_id:
            return JsonResponse({'success': False, 'message': 'Order not found'})
        
        order = get_object_or_404(Order, order_id=order_id)
        
        # For development/testing - simulate successful payment
        # In production, you would verify with actual Khalti API
        if True:  # Simulate successful verification
            # Update order with payment details
            order.khalti_token = token
            order.khalti_transaction_id = f"test_txn_{uuid.uuid4().hex[:8]}"
            order.payment_status = 'completed'
            order.status = 'processing'
            order.save()
            
            # Clear cart
            cart = get_or_create_cart(request)
            cart.items.all().delete()
            
            # Clear order_id from session
            if 'order_id' in request.session:
                del request.session['order_id']
            
            return JsonResponse({
                'success': True,
                'message': 'Payment successful',
                'order_id': str(order.order_id)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Payment verification failed'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing payment: {str(e)}'
        })

# Alternative real Khalti verification for production
def khalti_verify_production(request):
    """
    Use this function for actual Khalti integration in production
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'})
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        amount = data.get('amount')
        order_id = request.session.get('order_id')
        
        if not order_id:
            return JsonResponse({'success': False, 'message': 'Order not found'})
        
        order = get_object_or_404(Order, order_id=order_id)
        
        # Verify with Khalti (production environment)
        verification_url = 'https://khalti.com/api/v2/payment/verify/'
        headers = {
            'Authorization': 'Key test_secret_key_f59e8b7d18b4499bb4af332897a8f2dc'
        }
        payload = {
            'token': token,
            'amount': amount
        }
        
        response = requests.post(verification_url, data=payload, headers=headers)
        
        if response.status_code == 200:
            verification_data = response.json()
            
            # Update order with payment details
            order.khalti_token = token
            order.khalti_transaction_id = verification_data.get('idx')
            order.payment_status = 'completed'
            order.status = 'processing'
            order.save()
            
            # Clear cart
            cart = get_or_create_cart(request)
            cart.items.all().delete()
            
            # Clear order_id from session
            if 'order_id' in request.session:
                del request.session['order_id']
            
            return JsonResponse({
                'success': True,
                'message': 'Payment successful',
                'order_id': str(order.order_id)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Payment verification failed'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing payment: {str(e)}'
        })

def payment_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'store/payment_success.html', {'order': order})

def payment_failed(request):
    return render(request, 'store/payment_failed.html')

def order_history(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
    else:
        orders = []
    
    return render(request, 'store/order_history.html', {'orders': orders})

def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    # Check if user can view this order
    if request.user.is_authenticated:
        if order.user != request.user and not request.user.is_staff:
            messages.error(request, 'You do not have permission to view this order')
            return redirect('store:order_history')
    else:
        # For anonymous users, you might want to add additional verification
        pass
    
    return render(request, 'store/order_detail.html', {'order': order})