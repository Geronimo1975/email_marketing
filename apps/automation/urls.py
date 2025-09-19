from django.urls import path
from . import views

app_name = "automation"

urlpatterns = [
    # Template Views
    path("", views.AutomationDashboardView.as_view(), name="dashboard"),
    # API Views
    path("api/workflows/", views.WorkflowAPIView.as_view(), name="workflow_api"),
]
