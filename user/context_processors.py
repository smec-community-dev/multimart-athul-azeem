from .models import Cart, Wishlist

def cart_wishlist_counts(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return {
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
    }
