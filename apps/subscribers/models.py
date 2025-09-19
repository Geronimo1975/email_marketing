from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.validators import EmailValidator


class SubscriberList(models.Model):
    """Email subscriber lists for segmentation and organization."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='subscriber_lists'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_lists'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Subscriber List')
        verbose_name_plural = _('Subscriber Lists')
        db_table = 'subscriber_lists'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def subscriber_count(self):
        return self.subscribers.filter(is_active=True).count()


class Subscriber(models.Model):
    """Individual email subscribers with their data and preferences."""

    class Status(models.TextChoices):
        SUBSCRIBED = 'subscribed', _('Subscribed')
        UNSUBSCRIBED = 'unsubscribed', _('Unsubscribed')
        BOUNCED = 'bounced', _('Bounced')
        COMPLAINED = 'complained', _('Complained')
        PENDING = 'pending', _('Pending Confirmation')

    email = models.EmailField(validators=[EmailValidator()])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    lists = models.ManyToManyField(
        SubscriberList,
        through='Subscription',
        related_name='subscribers'
    )
    custom_fields = JSONField(default=dict, blank=True)
    tags = models.ManyToManyField('Tag', blank=True, related_name='subscribers')

    # Engagement metrics
    engagement_score = models.FloatField(default=0.0)
    last_activity = models.DateTimeField(null=True, blank=True)

    # Tracking fields
    source = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    preferred_language = models.CharField(max_length=10, default='en')

    # GDPR compliance
    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_date = models.DateTimeField(null=True, blank=True)

    # Odoo integration
    odoo_contact_id = models.IntegerField(null=True, blank=True, unique=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Subscriber')
        verbose_name_plural = _('Subscribers')
        db_table = 'subscribers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['odoo_contact_id']),
        ]

    def __str__(self):
        return f'{self.email} ({self.status})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def is_engaged(self):
        """Check if subscriber is considered engaged based on activity."""
        return self.engagement_score > 0.5


class Subscription(models.Model):
    """Through model for Subscriber-SubscriberList relationship."""

    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    subscriber_list = models.ForeignKey(SubscriberList, on_delete=models.CASCADE)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ['subscriber', 'subscriber_list']
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
        db_table = 'subscriptions'

    def __str__(self):
        return f'{self.subscriber.email} -> {self.subscriber_list.name}'


class Tag(models.Model):
    """Tags for organizing and segmenting subscribers."""

    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='tags'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'team']
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        db_table = 'tags'
        ordering = ['name']

    def __str__(self):
        return self.name


class SegmentRule(models.Model):
    """Dynamic segmentation rules for subscriber targeting."""

    class Operator(models.TextChoices):
        EQUALS = 'equals', _('Equals')
        NOT_EQUALS = 'not_equals', _('Not Equals')
        CONTAINS = 'contains', _('Contains')
        NOT_CONTAINS = 'not_contains', _('Does Not Contain')
        GREATER_THAN = 'gt', _('Greater Than')
        LESS_THAN = 'lt', _('Less Than')
        IN_LIST = 'in', _('In List')
        NOT_IN_LIST = 'not_in', _('Not In List')

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='segment_rules'
    )
    field_name = models.CharField(max_length=100)  # e.g., 'custom_fields.industry'
    operator = models.CharField(max_length=20, choices=Operator.choices)
    value = models.TextField()  # JSON-encoded value
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Segment Rule')
        verbose_name_plural = _('Segment Rules')
        db_table = 'segment_rules'
        ordering = ['-created_at']

    def __str__(self):
        return self.name