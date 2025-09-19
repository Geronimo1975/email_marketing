from django.urls import path
from . import views

app_name = "campaigns"

urlpatterns = [
    # Template Views
    path("", views.CampaignListView.as_view(), name="campaign_list"),
    # API Views
    path("api/", views.CampaignAPIView.as_view(), name="campaign_api"),
]
