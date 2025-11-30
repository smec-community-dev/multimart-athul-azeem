from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Notification
from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def seller_notifications_page(request):
    """Render the seller full notification page with search + filters."""

    user = request.user
    print(user)

    notifications = Notification.objects.filter(user=user).order_by("-created_at")
    print(notifications)

    # ----- SEARCH -----
    search_q = request.GET.get("search")
    if search_q:
        notifications = notifications.filter(
            title__icontains=search_q
        ) | notifications.filter(
            body__icontains=search_q
        )

    # ----- STATUS FILTER -----
    status = request.GET.get("status")
    if status == "unread":
        notifications = notifications.filter(is_read=False)
    elif status == "read":
        notifications = notifications.filter(is_read=True)

    # ----- PAGINATION -----
    paginator = Paginator(notifications, 10)   # 10 per page
    page_number = request.GET.get("page")
    notifications_page = paginator.get_page(page_number)
    print("REQUEST USER ID:", request.user.id)
    print("REQUEST USERNAME:", request.user.username)

    return render(
        request,
        "seller/notifications.html",
        {
            "notifications": notifications_page,
        }
    )



# 📌 1) Return full notification list (latest first)
@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    data = []
    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
            "extra": n.extra,
        })

    return JsonResponse({"notifications": data})


# 📌 2) Unread count for badge 🔔
@login_required
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})


# 📌 3) Mark notification as read when clicked
@login_required
def mark_as_read(request, notif_id):
    try:
        notif = Notification.objects.get(id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False, "error": "Notification not found"})
