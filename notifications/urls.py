# notifications/urls.py (unchanged, already correct)
from django.urls import path
from . import views

app_name = 'not'  # Add this if missing for namespacing

urlpatterns = [
    path('seller/', views.seller_notifications_page, name='seller_notifications_page'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('unread-count/', views.unread_notifications_count, name='unread_count'),
    path('list/', views.notifications_dropdown_list, name='list'),
    path("user/notifications/", views.user_notifications_page, name="user_notifications"),
]