from django.contrib.auth.decorators import login_required  # Add if missing
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import Notification  # ← Add this import
from django.contrib.auth import get_user_model  # If needed elsewhere

User = get_user_model()  # Keep if used, but prefer importing models


@login_required  # ← Renamed from seller_notifications_page
def seller_notifications_page(request):  # ← Generic name
    """Render the full notification page with search + filters (shared for sellers/users)."""

    user = request.user

    notifications = Notification.objects.filter(user=user).order_by("-created_at")

    # ----- SEARCH -----
    search_q = request.GET.get("search")
    if search_q:
        notifications = notifications.filter(
            Q(title__icontains=search_q) | Q(body__icontains=search_q)
        )

    # ----- STATUS FILTER -----
    status = request.GET.get("status")
    if status == "unread":
        notifications = notifications.filter(is_read=False)
    elif status == "read":
        notifications = notifications.filter(is_read=True)

    # ----- PAGINATION -----
    paginator = Paginator(notifications, 10)  # 10 per page
    page_number = request.GET.get("page")
    notifications_page = paginator.get_page(page_number)

    # ← NEW: Pass role info for template conditionals
    context = {
        "notifications": notifications_page,
        "is_seller": hasattr(user, 'seller_details'),  # ← Detect seller for UI tweaks
    }

    # ← Changed to generic template (create notifications/notifications.html if needed)
    return render(
        request,
        "seller/notifications.html",  # ← Generic path
        context
    )


@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):  # ← Renamed param for clarity
    """Mark a single notification as read via AJAX (generic)."""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.is_read = True
        notification.save(update_fields=['is_read'])  # ← Efficient update
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False, "error": "Notification not found"}, status=404)


@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all unread notifications as read via AJAX (generic)."""
    if not request.user.is_authenticated:  # ← NEW: Explicit unauth handling
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)

    updated_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)  # ← Bulk update, no save() needed
    return JsonResponse({
        "success": True,
        "updated_count": updated_count
    })


def unread_notifications_count(request):  # ← Renamed for consistency
    """Get the count of unread notifications for the badge (generic)."""
    if not request.user.is_authenticated:
        return JsonResponse({"unread_count": 0})

    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    return JsonResponse({"unread_count": count})


def notifications_dropdown_list(request):  # ← Renamed for consistency
    """Get the latest 5 notifications for the dropdown (generic)."""
    if not request.user.is_authenticated:
        return JsonResponse({"notifications": []})

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")[:5]

    data = [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_read": n.is_read,
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data})