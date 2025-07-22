from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart-count/', views.cart_count, name='cart_count'),
    
    # Checkout and Payment URLs
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<uuid:order_id>/', views.payment, name='payment'),
    path('khalti-verify/', views.khalti_verify, name='khalti_verify'),
    path('payment-success/<uuid:order_id>/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    
    # Authentication URLs
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin URLs
    path('admin/products/', views.admin_product_list, name='admin_product_list'),
    path('admin/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin/products/<int:pk>/update/', views.admin_product_update, name='admin_product_update'),
    path('admin/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
]