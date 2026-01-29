// Bad Apples Orchard - Cart Management

document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners to all "Add to Cart" buttons
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');

    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const varietyId = this.getAttribute('data-variety-id');
            const varietyName = this.getAttribute('data-variety-name');

            // Get quantity from input if available, otherwise use 1.0
            const quantityInput = document.getElementById(`qty-${varietyId}`);
            const quantityLbs = quantityInput ? parseFloat(quantityInput.value) : 1.0;

            addToCart(varietyId, varietyName, quantityLbs);
        });
    });
});

async function addToCart(varietyId, varietyName, quantityLbs) {
    try {
        const response = await fetch('/api/cart/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                variety_id: parseInt(varietyId),
                quantity_lbs: quantityLbs
            })
        });

        const result = await response.json();

        if (response.ok) {
            showNotification(`Added ${quantityLbs}lbs of ${varietyName} to cart!`, 'success');
            updateCartCount(result.cart_size);
        } else {
            showNotification(result.error || 'Failed to add to cart', 'error');
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showNotification('Error adding to cart', 'error');
    }
}

async function removeFromCart(varietyId) {
    try {
        const response = await fetch('/api/cart/remove', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                variety_id: parseInt(varietyId)
            })
        });

        const result = await response.json();

        if (response.ok) {
            showNotification('Item removed from cart', 'success');
            updateCartCount(result.cart_size);
            location.reload(); // Refresh to update cart display
        } else {
            showNotification(result.error || 'Failed to remove item', 'error');
        }
    } catch (error) {
        console.error('Error removing from cart:', error);
        showNotification('Error removing item', 'error');
    }
}

function updateCartCount(count) {
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        cartCountElement.textContent = `(${count})`;
    }
}

function showNotification(message, type) {
    // Check if notification element exists
    let notification = document.getElementById('notification');

    if (!notification) {
        // Create notification element if it doesn't exist
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.className = 'notification';
        document.body.appendChild(notification);
    }

    notification.textContent = message;
    notification.className = 'notification ' + type;
    notification.classList.remove('hidden');

    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.add('hidden');
    }, 3000);
}
