from django.urls import path
from . import views

app_name = "subscribers"

urlpatterns = [
    # Template Views
    path("", views.SubscriberListView.as_view(), name="subscriber_list"),
    path("create/", views.SubscriberCreateView.as_view(), name="subscriber_create"),
    path("<int:pk>/", views.SubscriberDetailView.as_view(), name="subscriber_detail"),
    # API Views
    path("api/", views.SubscriberAPIView.as_view(), name="subscriber_api"),
]
