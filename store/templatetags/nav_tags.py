from django import template
from django.urls import reverse, resolve
from django.http import Http404

register = template.Library()

@register.simple_tag(takes_context=True)
def active_page(context, url_name, **kwargs):
    """
    Returns 'active' if the current page matches the given URL name.
    Usage: {% active_page 'store:product_list' %}
    """
    request = context['request']
    try:
        # Get the current URL name
        current_url_name = resolve(request.path_info).url_name
        
        # Check if current URL name matches
        if current_url_name == url_name.split(':')[-1]:
            return 'active'
        
        # Also check the full namespaced URL
        try:
            target_url = reverse(url_name, kwargs=kwargs)
            if request.path == target_url:
                return 'active'
        except:
            pass
            
    except:
        pass
    
    return ''

@register.simple_tag(takes_context=True)
def is_active_section(context, *url_names):
    """
    Returns 'active' if any of the URL names match the current page.
    Usage: {% is_active_section 'store:admin_dashboard' 'store:admin_order_list' %}
    """
    request = context['request']
    try:
        current_url_name = resolve(request.path_info).url_name
        
        for url_name in url_names:
            if current_url_name == url_name.split(':')[-1]:
                return 'active'
                
    except:
        pass
    
    return ''

@register.simple_tag(takes_context=True)
def nav_class(context, url_name, base_class="nav-link px-3 rounded-pill fw-semibold", active_class="active-nav-item", **kwargs):
    """
    Returns CSS classes for navigation items.
    """
    is_active = active_page(context, url_name, **kwargs)
    if is_active == 'active':
        return f"{base_class} {active_class}"
    return f"{base_class} text-white"

@register.simple_tag(takes_context=True)
def admin_nav_class(context, *url_names):
    """
    Returns CSS classes for admin navigation items.
    """
    is_active = is_active_section(context, *url_names)
    base_class = "nav-link px-3 rounded-pill fw-semibold"
    if is_active == 'active':
        return f"{base_class} active-admin-nav"
    return f"{base_class} text-white"

@register.simple_tag(takes_context=True)
def page_title(context):
    """
    Returns the current page title based on URL name.
    """
    request = context['request']
    try:
        current_url_name = resolve(request.path_info).url_name
        
        page_titles = {
            'product_list': 'Products',
            'product_detail': 'Product Details',
            'cart_detail': 'Shopping Cart',
            'checkout': 'Checkout',
            'order_history': 'My Orders',
            'order_detail': 'Order Details',
            'admin_dashboard': 'Admin Dashboard',
            'admin_order_list': 'Order Management',
            'admin_order_detail': 'Order Details',
            'admin_order_update_status': 'Update Order Status',
            'admin_product_list': 'Product Management',
            'admin_product_create': 'Add New Product',
            'admin_product_update': 'Edit Product',
            'admin_product_delete': 'Delete Product',
            'payment': 'Payment',
            'payment_success': 'Payment Successful',
            'payment_failed': 'Payment Failed',
        }
        
        return page_titles.get(current_url_name, 'Page')
        
    except:
        return 'Page'

@register.simple_tag(takes_context=True)
def page_icon(context):
    """
    Returns the current page icon based on URL name.
    """
    request = context['request']
    try:
        current_url_name = resolve(request.path_info).url_name
        
        page_icons = {
            'product_list': 'bi-box-seam',
            'product_detail': 'bi-box',
            'cart_detail': 'bi-cart4',
            'checkout': 'bi-credit-card',
            'order_history': 'bi-clock-history',
            'order_detail': 'bi-receipt',
            'admin_dashboard': 'bi-speedometer2',
            'admin_order_list': 'bi-list-check',
            'admin_order_detail': 'bi-receipt-cutoff',
            'admin_order_update_status': 'bi-pencil-square',
            'admin_product_list': 'bi-box-seam',
            'admin_product_create': 'bi-plus-circle',
            'admin_product_update': 'bi-pencil-square',
            'admin_product_delete': 'bi-trash',
            'payment': 'bi-credit-card',
            'payment_success': 'bi-check-circle',
            'payment_failed': 'bi-x-circle',
        }
        
        return page_icons.get(current_url_name, 'bi-house')
        
    except:
        return 'bi-house'
