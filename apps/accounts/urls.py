from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('api/auth/', views.AuthAPIView.as_view(), name='api_auth'),
]