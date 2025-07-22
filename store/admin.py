from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'stock', 'available', 'featured', 'created_at']
    list_filter = ['available', 'featured', 'category', 'created_at']
    list_editable = ['price', 'stock', 'available', 'featured']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_total_price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'get_full_name', 'email', 'total_amount', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    list_editable = ['status']
    search_fields = ['order_id', 'email', 'first_name', 'last_name']
    readonly_fields = ['order_id', 'khalti_token', 'khalti_transaction_id', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'status', 'payment_status', 'payment_method', 'total_amount')
        }),
        ('Customer Information', {
            'fields': ('user', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('Shipping Information', {
            'fields': ('address', 'city', 'postal_code', 'country')
        }),
        ('Payment Information', {
            'fields': ('khalti_token', 'khalti_transaction_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'created_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']