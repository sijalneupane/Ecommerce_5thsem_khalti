document.addEventListener('DOMContentLoaded', function() {
    // Update cart count on page load
    updateCartCount();
    
    // Handle add to cart forms with AJAX
    const addToCartForms = document.querySelectorAll('form[action*="add-to-cart"]');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            
            // Add loading state
            submitButton.innerHTML = '<span class="loading"></span> Adding...';
            submitButton.disabled = true;
            
            const formData = new FormData(form);
            const url = form.action;
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    updateCartCount();
                    
                    // Add visual feedback
                    submitButton.innerHTML = '✓ Added!';
                    submitButton.classList.add('btn-success');
                    
                    setTimeout(() => {
                        submitButton.innerHTML = originalText;
                        submitButton.classList.remove('btn-success');
                        submitButton.disabled = false;
                    }, 1500);
                } else {
                    showNotification('Error adding item to cart', 'error');
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error adding item to cart', 'error');
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            });
        });
    });
    
    // Enhanced quantity input handling
    const quantityInputs = document.querySelectorAll('input[name="quantity"]');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const form = this.closest('form');
            if (form && form.action.includes('update-cart')) {
                // Auto-submit form when quantity changes
                setTimeout(() => {
                    form.submit();
                }, 500);
            }
        });
    });
});

function updateCartCount() {
    fetch('/store/cart-count/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        const cartCountElement = document.getElementById('cart-count');
        if (cartCountElement) {
            cartCountElement.textContent = data.count || 0;
            
            // Add animation when count changes
            cartCountElement.style.transform = 'scale(1.5)';
            setTimeout(() => {
                cartCountElement.style.transform = 'scale(1)';
            }, 200);
        }
    })
    .catch(error => {
        console.error('Error updating cart count:', error);
    });
}

function showNotification(message, type) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.floating-notification');
    existingNotifications.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show floating-notification`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideInRight 0.3s ease-out;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    `;
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
            ${message}
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .floating-notification {
        border: none !important;
        backdrop-filter: blur(10px);
    }
    
    #cart-count {
        transition: transform 0.3s ease;
    }
`;
document.head.appendChild(style);

// Quantity input validation
document.addEventListener('input', function(e) {
    if (e.target.type === 'number' && e.target.name === 'quantity') {
        const value = parseInt(e.target.value);
        if (value < 1) {
            e.target.value = 1;
        }
    }
});