"""
URL configuration for email_marketing project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/campaigns/', include('apps.campaigns.urls')),
    path('api/subscribers/', include('apps.subscribers.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/automation/', include('apps.automation.urls')),
    path('api/accounts/', include('apps.accounts.urls')),
    path('webhooks/', include('apps.integrations.urls')),
    path('', include(('apps.campaigns.urls', 'campaigns'), namespace='frontend')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add debug toolbar URLs
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
