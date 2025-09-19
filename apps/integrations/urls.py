"""
URLs for integrations app.
"""

from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Webhook endpoints
    path('mailgun/', views.MailgunWebhookView.as_view(), name='mailgun_webhook'),
    path('odoo/', views.OdooWebhookView.as_view(), name='odoo_webhook'),

    # API endpoints
    path('sync-odoo/', views.SyncOdooContactsView.as_view(), name='sync_odoo_contacts'),
    path('validate-email/', views.ValidateEmailView.as_view(), name='validate_email'),
    path('suppressions/', views.SuppressionListView.as_view(), name='suppressions'),
]