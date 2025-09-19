from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.utils import timezone


class EmailEvent(models.Model):
    """Tracks all email events from Mailgun webhooks."""

    class EventType(models.TextChoices):
        DELIVERED = 'delivered', _('Delivered')
        OPENED = 'opened', _('Opened')
        CLICKED = 'clicked', _('Clicked')
        UNSUBSCRIBED = 'unsubscribed', _('Unsubscribed')
        COMPLAINED = 'complained', _('Complained')
        BOUNCED = 'bounced', _('Bounced')
        FAILED = 'failed', _('Failed')

    # Core event data
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    timestamp = models.DateTimeField()

    # Message identification
    mailgun_message_id = models.CharField(max_length=255, db_index=True)
    mailgun_event_id = models.CharField(max_length=255, unique=True)

    # Recipient information
    recipient_email = models.EmailField(db_index=True)
    subscriber = models.ForeignKey(
        'subscribers.Subscriber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_events'
    )

    # Campaign information
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_events'
    )
    campaign_recipient = models.ForeignKey(
        'campaigns.CampaignRecipient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_events'
    )

    # Event-specific data
    url = models.URLField(blank=True)  # For click events
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    client_name = models.CharField(max_length=100, blank=True)
    client_os = models.CharField(max_length=100, blank=True)

    # Bounce/failure specific
    bounce_reason = models.TextField(blank=True)
    bounce_code = models.CharField(max_length=10, blank=True)
    error_message = models.TextField(blank=True)

    # Geolocation data
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Raw webhook data
    raw_data = JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Email Event')
        verbose_name_plural = _('Email Events')
        db_table = 'email_events'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['campaign', 'event_type']),
            models.Index(fields=['subscriber', 'event_type']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f'{self.event_type} - {self.recipient_email} - {self.timestamp}'


class CampaignReport(models.Model):
    """Daily aggregated campaign performance reports."""

    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        related_name='daily_reports'
    )
    date = models.DateField()

    # Email counts
    emails_sent = models.IntegerField(default=0)
    emails_delivered = models.IntegerField(default=0)
    emails_bounced = models.IntegerField(default=0)
    emails_failed = models.IntegerField(default=0)

    # Engagement counts
    unique_opens = models.IntegerField(default=0)
    total_opens = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)

    # Negative actions
    unsubscribes = models.IntegerField(default=0)
    complaints = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['campaign', 'date']
        verbose_name = _('Campaign Report')
        verbose_name_plural = _('Campaign Reports')
        db_table = 'campaign_reports'
        ordering = ['-date']

    def __str__(self):
        return f'{self.campaign.name} - {self.date}'

    @property
    def open_rate(self):
        if self.emails_delivered > 0:
            return (self.unique_opens / self.emails_delivered) * 100
        return 0

    @property
    def click_rate(self):
        if self.emails_delivered > 0:
            return (self.unique_clicks / self.emails_delivered) * 100
        return 0

    @property
    def bounce_rate(self):
        if self.emails_sent > 0:
            return (self.emails_bounced / self.emails_sent) * 100
        return 0


class SubscriberActivity(models.Model):
    """Tracks subscriber engagement across all campaigns."""

    subscriber = models.OneToOneField(
        'subscribers.Subscriber',
        on_delete=models.CASCADE,
        related_name='activity_summary'
    )

    # Email counts
    emails_received = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)

    # Engagement metrics
    first_opened = models.DateTimeField(null=True, blank=True)
    last_opened = models.DateTimeField(null=True, blank=True)
    first_clicked = models.DateTimeField(null=True, blank=True)
    last_clicked = models.DateTimeField(null=True, blank=True)

    # Calculated scores
    engagement_score = models.FloatField(default=0.0)
    activity_score = models.FloatField(default=0.0)

    # Behavioral data
    preferred_send_time = models.TimeField(null=True, blank=True)
    preferred_day_of_week = models.IntegerField(null=True, blank=True)  # 0=Monday
    most_clicked_link_type = models.CharField(max_length=100, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Subscriber Activity')
        verbose_name_plural = _('Subscriber Activities')
        db_table = 'subscriber_activities'

    def __str__(self):
        return f'Activity: {self.subscriber.email}'

    @property
    def open_rate(self):
        if self.emails_received > 0:
            return (self.emails_opened / self.emails_received) * 100
        return 0

    @property
    def click_rate(self):
        if self.emails_received > 0:
            return (self.emails_clicked / self.emails_received) * 100
        return 0

    def update_engagement_score(self):
        """Calculate and update engagement score based on activity."""
        if self.emails_received == 0:
            self.engagement_score = 0.0
            return

        # Base score from open and click rates
        open_score = min(self.open_rate / 100, 1.0) * 0.6
        click_score = min(self.click_rate / 100, 1.0) * 0.4

        # Recency bonus
        recency_bonus = 0.0
        if self.last_opened:
            days_since_last_open = (timezone.now() - self.last_opened).days
            if days_since_last_open <= 7:
                recency_bonus = 0.2
            elif days_since_last_open <= 30:
                recency_bonus = 0.1

        self.engagement_score = min((open_score + click_score + recency_bonus), 1.0)
        self.save(update_fields=['engagement_score'])


class LinkClick(models.Model):
    """Detailed tracking of link clicks in emails."""

    email_event = models.OneToOneField(
        EmailEvent,
        on_delete=models.CASCADE,
        related_name='link_click_detail'
    )
    url = models.URLField()
    link_text = models.CharField(max_length=255, blank=True)
    link_position = models.IntegerField(null=True, blank=True)  # Position in email

    # Categorization
    link_category = models.CharField(max_length=100, blank=True)
    is_tracked = models.BooleanField(default=True)

    # Context
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        related_name='link_clicks'
    )
    subscriber = models.ForeignKey(
        'subscribers.Subscriber',
        on_delete=models.CASCADE,
        related_name='link_clicks'
    )

    clicked_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Link Click')
        verbose_name_plural = _('Link Clicks')
        db_table = 'link_clicks'
        ordering = ['-clicked_at']
        indexes = [
            models.Index(fields=['campaign', 'url']),
            models.Index(fields=['clicked_at']),
        ]

    def __str__(self):
        return f'{self.subscriber.email} clicked {self.url}'


class DomainReputation(models.Model):
    """Tracks sending domain reputation metrics."""

    domain = models.CharField(max_length=255, unique=True)

    # Reputation scores (0-100)
    sender_score = models.FloatField(default=0.0)
    reputation_score = models.FloatField(default=0.0)

    # Delivery metrics
    total_sent = models.BigIntegerField(default=0)
    total_delivered = models.BigIntegerField(default=0)
    total_bounced = models.BigIntegerField(default=0)
    total_complaints = models.BigIntegerField(default=0)

    # ISP-specific metrics
    gmail_delivery_rate = models.FloatField(default=0.0)
    outlook_delivery_rate = models.FloatField(default=0.0)
    yahoo_delivery_rate = models.FloatField(default=0.0)

    # Blacklist status
    is_blacklisted = models.BooleanField(default=False)
    blacklist_sources = JSONField(default=list, blank=True)

    last_checked = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Domain Reputation')
        verbose_name_plural = _('Domain Reputations')
        db_table = 'domain_reputations'
        ordering = ['-reputation_score']

    def __str__(self):
        return f'{self.domain} (Score: {self.reputation_score})'

    @property
    def delivery_rate(self):
        if self.total_sent > 0:
            return (self.total_delivered / self.total_sent) * 100
        return 0

    @property
    def complaint_rate(self):
        if self.total_delivered > 0:
            return (self.total_complaints / self.total_delivered) * 100
        return 0