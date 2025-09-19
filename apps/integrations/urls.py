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
    path('api/sync/odoo/contacts/', views.SyncOdooContactsView.as_view(), name='sync_odoo_contacts'),
    path('api/validate/email/', views.ValidateEmailView.as_view(), name='validate_email'),
    path('api/suppressions/', views.SuppressionListView.as_view(), name='suppressions'),
]