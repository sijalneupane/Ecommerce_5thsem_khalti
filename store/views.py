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
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from functools import wraps
import json
import requests
import uuid

from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import ProductForm, SearchForm, SignupForm, CheckoutForm


def non_admin_required(view_func):
    """Decorator to redirect admin users to admin dashboard"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return redirect('store:admin_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
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
            # Get session key before login to merge carts
            session_key = request.session.session_key
            
            login(request, user)
            
            # Merge session cart with user cart after login
            if session_key:
                merge_carts(user, session_key)
            
            # Check for next parameter to redirect after login
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Default redirect based on user type
            if user.is_staff or user.is_superuser:
                return redirect('store:admin_dashboard')
            else:
                return redirect('store:product_list')
        else:
            messages.error(request, "Invalid credentials.")
    
    # Get next parameter for the login form
    next_url = request.GET.get('next', '')
    return render(request, 'store/login.html', {'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    return redirect('store:product_list')
@non_admin_required
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

@non_admin_required
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

def merge_carts(user, session_key):
    """Merge session cart with user cart after login"""
    try:
        # Get session cart
        session_cart = Cart.objects.get(session_key=session_key)
        
        # Get or create user cart
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        # Merge cart items
        for session_item in session_cart.items.all():
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=session_item.product,
                defaults={'quantity': session_item.quantity}
            )
            if not created:
                # If item already exists, add quantities
                user_item.quantity += session_item.quantity
                user_item.save()
        
        # Delete session cart after merging
        session_cart.delete()
        
    except Cart.DoesNotExist:
        # No session cart to merge
        pass

@require_POST
@non_admin_required
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

@non_admin_required
def cart_detail(request):
    cart = get_or_create_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

def cart_count(request):
    # Return 0 for admin users
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'count': 0})
        
    cart = get_or_create_cart(request)
    count = cart.get_total_items() if cart else 0
    return JsonResponse({'count': count})

@require_POST
@non_admin_required
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

@non_admin_required
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
def admin_dashboard(request):
    # Get recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Get order statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(payment_status='completed').count()
    
    # Get product statistics
    total_products = Product.objects.count()
    available_products = Product.objects.filter(available=True).count()
    low_stock_products = Product.objects.filter(stock__lt=10, available=True).count()
    
    context = {
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_products': total_products,
        'available_products': available_products,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'store/admin/dashboard.html', context)

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

# Admin Order Views
@login_required
@user_passes_test(is_admin)
def admin_order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Filter by payment status
    payment_status_filter = request.GET.get('payment_status')
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'current_status': status_filter,
        'current_payment_status': payment_status_filter,
        'search_query': search_query,
    }
    return render(request, 'store/admin/order_list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/admin/order_detail.html', context)

@login_required
@user_passes_test(is_admin)
def admin_order_update_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_payment_status = request.POST.get('payment_status')
        
        if new_status and new_status in [choice[0] for choice in Order.STATUS_CHOICES]:
            order.status = new_status
            
        if new_payment_status and new_payment_status in [choice[0] for choice in Order.PAYMENT_STATUS_CHOICES]:
            order.payment_status = new_payment_status
            
        order.save()
        messages.success(request, f'Order {order.order_id} status updated successfully')
        return redirect('store:admin_order_detail', order_id=order.order_id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'store/admin/order_update_status.html', context)

# Checkout and Payment Views
@non_admin_required
def checkout(request):
    # Check if user is authenticated before proceeding with checkout
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to proceed with checkout.')
        login_url = reverse('store:login')
        checkout_url = reverse('store:checkout')
        return redirect(f'{login_url}?next={checkout_url}')
    
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

@non_admin_required
def payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    # Store order_id in session for verification
    request.session['order_id'] = str(order_id)
    
    # Khalti KPG-2 configuration for sandbox
    khalti_config = {
        'secret_key': 'test_secret_key_f59e8b7d18b4499bb4af332897a8f2dc',
        'base_url': 'https://dev.khalti.com/api/v2/',  # Sandbox URL
        'test_mode': True
    }
    
    context = {
        'order': order,
        'khalti_config': khalti_config,
        'amount_in_paisa': int(order.total_amount * 100),  # Khalti expects amount in paisa
    }
    return render(request, 'store/payment.html', context)

@csrf_exempt
def khalti_initiate(request):
    """Initiate Khalti payment using KPG-2 API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'})
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'success': False, 'message': 'Order ID is required'})
        
        order = get_object_or_404(Order, order_id=order_id)
        
        # Khalti payment initiation API call
        initiate_url = 'https://dev.khalti.com/api/v2/epayment/initiate/'
        
        # TODO: Replace this with your actual test secret key from https://test-admin.khalti.com
        # Using the sample key from documentation for testing
        secret_key = '05bf95cc57244045b8df5fad06748dab'
        
        headers = {
            'Authorization': f'key {secret_key}',  # Note: lowercase 'key'
            'Content-Type': 'application/json',
        }
        
        # Build the return URL (make sure this is accessible)
        return_url = request.build_absolute_uri('/store/khalti-callback/')
        website_url = request.build_absolute_uri('/')
        
        payload = {
            "return_url": return_url,
            "website_url": website_url,
            "amount": int(order.total_amount * 100),  # Amount in paisa
            "purchase_order_id": str(order.order_id),
            "purchase_order_name": f"Order #{order.order_id}",
            "customer_info": {
                "name": order.get_full_name(),
                "email": order.email,
                "phone": order.phone
            },
            "amount_breakdown": [
                {
                    "label": "Total Amount",
                    "amount": int(order.total_amount * 100)
                }
            ],
            "product_details": [
                {
                    "identity": str(item.product.id),
                    "name": item.product.name,
                    "total_price": int(item.get_total_price() * 100),
                    "quantity": item.quantity,
                    "unit_price": int(item.product.price * 100)
                } for item in order.items.all()
            ]
        }
        
        response = requests.post(initiate_url, json=payload, headers=headers, timeout=30)
        
        print(f"Khalti initiate request:")
        print(f"URL: {initiate_url}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            payment_data = response.json()
            
            # Store pidx in session for later verification
            request.session['khalti_pidx'] = payment_data.get('pidx')
            
            return JsonResponse({
                'success': True,
                'payment_url': payment_data.get('payment_url'),
                'pidx': payment_data.get('pidx'),
                'expires_at': payment_data.get('expires_at'),
                'expires_in': payment_data.get('expires_in')
            })
        else:
            error_data = response.json() if response.content else {}
            print(f"Khalti initiation failed: {response.status_code} - {response.text}")
            return JsonResponse({
                'success': False,
                'message': 'Payment initiation failed',
                'error': error_data
            })
            
    except requests.exceptions.RequestException as e:
        print(f"Network error during Khalti initiation: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Network error during payment initiation. Please try again.'
        })
    except Exception as e:
        print(f"Unexpected error during Khalti initiation: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        })

def khalti_callback(request):
    """Handle Khalti payment callback"""
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')
    transaction_id = request.GET.get('transaction_id')
    
    if not pidx:
        messages.error(request, 'Invalid payment callback')
        return redirect('store:product_list')
    
    # Verify the pidx matches what we stored
    session_pidx = request.session.get('khalti_pidx')
    if pidx != session_pidx:
        messages.error(request, 'Payment verification failed')
        return redirect('store:product_list')
    
    if status == 'Completed':
        # Verify payment with lookup API
        lookup_url = 'https://dev.khalti.com/api/v2/epayment/lookup/'
        secret_key = '05bf95cc57244045b8df5fad06748dab'
        headers = {
            'Authorization': f'key {secret_key}',  # Note: lowercase 'key'
            'Content-Type': 'application/json',
        }
        payload = {"pidx": pidx}
        
        try:
            response = requests.post(lookup_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                verification_data = response.json()
                
                if verification_data.get('status') == 'Completed':
                    # Update order
                    order_id = request.session.get('order_id')
                    if order_id:
                        order = get_object_or_404(Order, order_id=order_id)
                        order.khalti_transaction_id = verification_data.get('transaction_id')
                        order.payment_status = 'completed'
                        order.status = 'processing'
                        order.save()
                        
                        # Clear cart and session
                        cart = get_or_create_cart(request)
                        cart.items.all().delete()
                        
                        if 'order_id' in request.session:
                            del request.session['order_id']
                        if 'khalti_pidx' in request.session:
                            del request.session['khalti_pidx']
                        
                        return redirect('store:payment_success', order_id=order.order_id)
                
            messages.error(request, 'Payment verification failed')
            return redirect('store:payment_failed')
            
        except Exception as e:
            print(f"Error during payment verification: {str(e)}")
            messages.error(request, 'Payment verification failed')
            return redirect('store:payment_failed')
    
    elif status == 'User canceled':
        messages.warning(request, 'Payment was canceled')
        return redirect('store:checkout')
    else:
        messages.error(request, f'Payment failed with status: {status}')
        return redirect('store:payment_failed')

@csrf_exempt
def khalti_verify(request):
    """Legacy verification endpoint - keeping for compatibility"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method allowed'})
    
    try:
        data = json.loads(request.body)
        pidx = data.get('pidx')
        
        if not pidx:
            return JsonResponse({'success': False, 'message': 'PIDX is required'})
        
        # Use the new lookup API
        lookup_url = 'https://dev.khalti.com/api/v2/epayment/lookup/'
        secret_key = '05bf95cc57244045b8df5fad06748dab'
        headers = {
            'Authorization': f'key {secret_key}',  # Note: lowercase 'key'
            'Content-Type': 'application/json',
        }
        payload = {"pidx": pidx}
        
        response = requests.post(lookup_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            verification_data = response.json()
            
            if verification_data.get('status') == 'Completed':
                order_id = request.session.get('order_id')
                if order_id:
                    order = get_object_or_404(Order, order_id=order_id)
                    order.khalti_transaction_id = verification_data.get('transaction_id')
                    order.payment_status = 'completed'
                    order.status = 'processing'
                    order.save()
                    
                    # Clear cart and session
                    cart = get_or_create_cart(request)
                    cart.items.all().delete()
                    
                    if 'order_id' in request.session:
                        del request.session['order_id']
                    if 'khalti_pidx' in request.session:
                        del request.session['khalti_pidx']
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Payment successful',
                        'order_id': str(order.order_id),
                        'transaction_id': verification_data.get('transaction_id')
                    })
            
            return JsonResponse({
                'success': False,
                'message': f'Payment not completed. Status: {verification_data.get("status")}'
            })
        else:
            print(f"Khalti lookup failed: {response.status_code} - {response.text}")
            return JsonResponse({
                'success': False,
                'message': f'Payment verification failed. Status: {response.status_code}'
            })
            
    except Exception as e:
        print(f"Error during Khalti verification: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred during verification'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        print(f"Error in khalti_verify: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error processing payment: {str(e)}'
        })

@non_admin_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'store/payment_success.html', {'order': order})

@csrf_exempt
@non_admin_required
def test_khalti_api(request):
    """Test Khalti API connectivity and credentials"""
    if request.method == 'GET':
        try:
            # Test the API with a simple request
            test_url = 'https://dev.khalti.com/api/v2/epayment/initiate/'
            secret_key = '05bf95cc57244045b8df5fad06748dab'
            
            headers = {
                'Authorization': f'key {secret_key}',  # Note: lowercase 'key'
                'Content-Type': 'application/json',
            }
            
            # Minimal test payload
            test_payload = {
                "return_url": "https://example.com/",
                "website_url": "https://example.com/",
                "amount": 1000,  # 10 NPR in paisa
                "purchase_order_id": "test_order_123",
                "purchase_order_name": "Test Order",
                "customer_info": {
                    "name": "Test Customer",
                    "email": "test@example.com",
                    "phone": "9800000001"
                }
            }
            
            response = requests.post(test_url, json=test_payload, headers=headers, timeout=30)
            
            return JsonResponse({
                'status_code': response.status_code,
                'response_text': response.text,
                'headers_sent': headers,
                'payload_sent': test_payload
            })
            
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'message': 'Failed to test Khalti API'
            })
    
    return JsonResponse({'message': 'Use GET request to test'})

@non_admin_required
def payment_failed(request):
    return render(request, 'store/payment_failed.html')

@non_admin_required
def order_history(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
    else:
        orders = []
    
    return render(request, 'store/order_history.html', {'orders': orders})

@non_admin_required
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