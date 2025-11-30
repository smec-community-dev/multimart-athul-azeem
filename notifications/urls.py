from django.urls import path

from seller.urls import app_name
from .views import get_notifications, unread_count, mark_as_read,seller_notifications_page
app_name='not'
urlpatterns = [
    path('list/', get_notifications, name='notifications_list'),
    path('unread-count/', unread_count, name='notifications_unread'),
    path('mark-read/<int:notif_id>/', mark_as_read, name='notification_mark_read'),
    path('seller/', seller_notifications_page, name='seller_notifications_page'),
]
