from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .utils import notify_seller, notify_user

# EDIT these two imports to match your apps
from user.models import Order        # <-- change if your app name is different
from user.models import Review     # <-- change if Review lives in another app

@receiver(pre_save, sender=Order)
def capture_order_old_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    try:
        old = Order.objects.get(pk=instance.pk)
        instance._old_status = old.status
    except Order.DoesNotExist:
        instance._old_status = None

@receiver(post_save, sender=Order)
def order_created_or_updated(sender, instance, created, **kwargs):
    if created:
        seller = instance.seller
        if seller:
            seller_user_id = seller.user.id if hasattr(seller, "user") else seller.id
            title = "New Order Received"
            body = f"Order #{instance.id} placed. ₹{instance.total_amount}"
            extra = {"order_id": instance.id}
            notify_seller(seller_user_id, title, body, extra)
        return

    old_status = getattr(instance, "_old_status", None)
    new_status = instance.status
    if old_status != new_status:
        user = instance.user
        title = f"Order #{instance.id} status updated"
        first_item_name = instance.items.first().product.name if instance.items.exists() else "an item"
        body = f"Your order for {first_item_name} is now '{new_status}'."
        extra = {"order_id": instance.id, "old_status": old_status, "new_status": new_status}
        notify_user(user.id, title, body, extra)


@receiver(pre_save, sender=Review)
def capture_review_old_approved(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_approved = None
        return
    try:
        old = Review.objects.get(pk=instance.pk)
        instance._old_approved = old.is_approved
    except Review.DoesNotExist:
        instance._old_approved = None

@receiver(post_save, sender=Review)
def review_created_or_approved(sender, instance, created, **kwargs):
    product = instance.product
    review_user = instance.user

    if created:
        product_owner = getattr(product, "seller", None) or getattr(product, "user", None)
        if product_owner:
            owner_user_id = product_owner.user.id if hasattr(product_owner, "user") else product_owner.id
            title = "New Review Submitted"
            body = f"New review for {product.name}: {instance.rating}⭐ - { (instance.comment or '')[:80] }"
            extra = {"product_id": product.id, "review_id": instance.id}
            notify_seller(owner_user_id, title, body, extra)
        return

    old_approved = getattr(instance, "_old_approved", None)
    if old_approved is False and instance.is_approved is True:
        title = "Your review was approved"
        body = f"Your review for {product.name} was approved."
        extra = {"product_id": product.id, "review_id": instance.id}
        notify_user(review_user.id, title, body, extra)
