from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.utils import timezone


class Integration(models.Model):
    """Base model for external service integrations."""

    class Provider(models.TextChoices):
        MAILGUN = 'mailgun', _('Mailgun')
        ODOO = 'odoo', _('Odoo CRM')
        ZAPIER = 'zapier', _('Zapier')
        WEBHOOK = 'webhook', _('Custom Webhook')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        ERROR = 'error', _('Error')
        PENDING = 'pending', _('Pending Setup')

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=50, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='integrations'
    )

    # Configuration
    config = JSONField(default=dict)  # Provider-specific settings
    credentials = models.TextField(blank=True)  # Encrypted credentials

    # Monitoring
    last_sync = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    error_count = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_integrations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Integration')
        verbose_name_plural = _('Integrations')
        db_table = 'integrations'
        ordering = ['-created_at']
        unique_together = ['team', 'provider']

    def __str__(self):
        return f'{self.name} ({self.provider})'

    def encrypt_credentials(self, credentials_dict):
        """Encrypt and store credentials (simplified for development)."""
        # For production, implement proper encryption
        import json
        self.credentials = json.dumps(credentials_dict)

    def decrypt_credentials(self):
        """Decrypt and return credentials (simplified for development)."""
        if not self.credentials:
            return {}
        import json
        try:
            return json.loads(self.credentials)
        except json.JSONDecodeError:
            return {}


class WebhookEndpoint(models.Model):
    """Webhook endpoints for receiving external events."""

    class EventType(models.TextChoices):
        MAILGUN_DELIVERY = 'mailgun_delivery', _('Mailgun Delivery')
        MAILGUN_ENGAGEMENT = 'mailgun_engagement', _('Mailgun Engagement')
        ODOO_CONTACT_UPDATE = 'odoo_contact_update', _('Odoo Contact Update')
        CUSTOM = 'custom', _('Custom Webhook')

    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    url_path = models.CharField(max_length=255, unique=True)

    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='webhook_endpoints'
    )

    # Security
    secret_key = models.CharField(max_length=255)
    verify_signature = models.BooleanField(default=True)

    # Processing settings
    is_active = models.BooleanField(default=True)
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=60)  # seconds

    # Statistics
    total_requests = models.BigIntegerField(default=0)
    successful_requests = models.BigIntegerField(default=0)
    failed_requests = models.BigIntegerField(default=0)
    last_request = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Webhook Endpoint')
        verbose_name_plural = _('Webhook Endpoints')
        db_table = 'webhook_endpoints'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.event_type})'

    @property
    def success_rate(self):
        if self.total_requests > 0:
            return (self.successful_requests / self.total_requests) * 100
        return 0


class WebhookLog(models.Model):
    """Log of webhook requests for debugging and monitoring."""

    class Status(models.TextChoices):
        SUCCESS = 'success', _('Success')
        FAILED = 'failed', _('Failed')
        RETRY = 'retry', _('Retry')
        IGNORED = 'ignored', _('Ignored')

    webhook_endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name='logs'
    )

    # Request details
    request_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices)

    # Request data
    headers = JSONField(default=dict)
    payload = JSONField(default=dict)
    signature = models.CharField(max_length=255, blank=True)

    # Processing details
    processing_time = models.FloatField(null=True, blank=True)  # milliseconds
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    # Response
    response_status = models.IntegerField(null=True, blank=True)
    response_data = JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Webhook Log')
        verbose_name_plural = _('Webhook Logs')
        db_table = 'webhook_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['webhook_endpoint', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.webhook_endpoint.name} - {self.status} - {self.created_at}'


class SyncJob(models.Model):
    """Background sync jobs for integrations."""

    class JobType(models.TextChoices):
        ODOO_IMPORT_CONTACTS = 'odoo_import_contacts', _('Odoo Import Contacts')
        ODOO_SYNC_CONTACTS = 'odoo_sync_contacts', _('Odoo Sync Contacts')
        ODOO_EXPORT_ENGAGEMENT = 'odoo_export_engagement', _('Odoo Export Engagement')
        MAILGUN_SYNC_SUPPRESSIONS = 'mailgun_sync_suppressions', _('Mailgun Sync Suppressions')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='sync_jobs'
    )

    job_type = models.CharField(max_length=50, choices=JobType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Job configuration
    config = JSONField(default=dict)  # Job-specific parameters

    # Progress tracking
    total_records = models.IntegerField(null=True, blank=True)
    processed_records = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    error_details = JSONField(default=dict, blank=True)

    # Results
    result_summary = JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='sync_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sync Job')
        verbose_name_plural = _('Sync Jobs')
        db_table = 'sync_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['integration', 'status']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.job_type} - {self.status} - {self.created_at}'

    @property
    def progress_percentage(self):
        if self.total_records and self.total_records > 0:
            return (self.processed_records / self.total_records) * 100
        return 0

    @property
    def success_rate(self):
        if self.processed_records > 0:
            return (self.successful_records / self.processed_records) * 100
        return 0

    def duration(self):
        """Calculate job duration."""
        if self.started_at:
            end_time = self.completed_at or timezone.now()
            return end_time - self.started_at
        return None