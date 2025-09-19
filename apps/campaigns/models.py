from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class EmailTemplate(models.Model):
    """Reusable email templates for campaigns."""

    class Type(models.TextChoices):
        CAMPAIGN = 'campaign', _('Campaign')
        AUTOMATION = 'automation', _('Automation')
        TRANSACTIONAL = 'transactional', _('Transactional')

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.CAMPAIGN)
    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='email_templates'
    )

    # Template content
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)

    # Template metadata
    variables = JSONField(default=list, blank=True)  # List of template variables
    thumbnail = models.ImageField(
        upload_to='template_thumbnails/',
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])]
    )

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Email Template')
        verbose_name_plural = _('Email Templates')
        db_table = 'email_templates'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Campaign(models.Model):
    """Email marketing campaigns."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SCHEDULED = 'scheduled', _('Scheduled')
        SENDING = 'sending', _('Sending')
        SENT = 'sent', _('Sent')
        PAUSED = 'paused', _('Paused')
        CANCELLED = 'cancelled', _('Cancelled')

    class Type(models.TextChoices):
        REGULAR = 'regular', _('Regular')
        AB_TEST = 'ab_test', _('A/B Test')
        RSS = 'rss', _('RSS Campaign')

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.REGULAR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='campaigns'
    )

    # Email content
    subject = models.CharField(max_length=255)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255)
    reply_to = models.EmailField(blank=True)

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns'
    )
    html_content = models.TextField()
    text_content = models.TextField(blank=True)

    # Targeting
    subscriber_lists = models.ManyToManyField(
        'subscribers.SubscriberList',
        related_name='campaigns'
    )
    segment_rules = models.ManyToManyField(
        'subscribers.SegmentRule',
        blank=True,
        related_name='campaigns'
    )
    tags = models.ManyToManyField(
        'subscribers.Tag',
        blank=True,
        related_name='campaigns'
    )

    # Scheduling
    send_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')

    # A/B Testing
    ab_test_percentage = models.IntegerField(default=100)  # Percentage of list to send to
    ab_winner_criteria = models.CharField(max_length=50, blank=True)  # 'open_rate', 'click_rate'
    ab_test_duration = models.IntegerField(default=24)  # Hours to wait before sending to remainder

    # Tracking settings
    track_opens = models.BooleanField(default=True)
    track_clicks = models.BooleanField(default=True)

    # Statistics (denormalized for performance)
    total_recipients = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    emails_delivered = models.IntegerField(default=0)
    emails_bounced = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)
    unsubscribes = models.IntegerField(default=0)
    complaints = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_campaigns'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Campaign')
        verbose_name_plural = _('Campaigns')
        db_table = 'campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['send_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return self.name

    @property
    def open_rate(self):
        if self.emails_delivered > 0:
            return (self.emails_opened / self.emails_delivered) * 100
        return 0

    @property
    def click_rate(self):
        if self.emails_delivered > 0:
            return (self.emails_clicked / self.emails_delivered) * 100
        return 0

    @property
    def bounce_rate(self):
        if self.emails_sent > 0:
            return (self.emails_bounced / self.emails_sent) * 100
        return 0

    def can_send(self):
        """Check if campaign can be sent."""
        return self.status in [self.Status.DRAFT, self.Status.SCHEDULED]

    def is_scheduled(self):
        """Check if campaign is scheduled for future sending."""
        return (
            self.status == self.Status.SCHEDULED and
            self.send_at and
            self.send_at > timezone.now()
        )


class CampaignRecipient(models.Model):
    """Individual recipients of a campaign with delivery tracking."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        BOUNCED = 'bounced', _('Bounced')
        FAILED = 'failed', _('Failed')

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    subscriber = models.ForeignKey(
        'subscribers.Subscriber',
        on_delete=models.CASCADE,
        related_name='campaign_recipients'
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    mailgun_message_id = models.CharField(max_length=255, blank=True)

    # Personalization data
    personalized_subject = models.CharField(max_length=255, blank=True)
    personalized_content = models.TextField(blank=True)

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    bounce_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['campaign', 'subscriber']
        verbose_name = _('Campaign Recipient')
        verbose_name_plural = _('Campaign Recipients')
        db_table = 'campaign_recipients'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['mailgun_message_id']),
        ]

    def __str__(self):
        return f'{self.campaign.name} -> {self.subscriber.email}'


class CampaignVariant(models.Model):
    """A/B test variants for campaigns."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    name = models.CharField(max_length=100)  # e.g., 'Variant A', 'Variant B'

    # Variant content
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)

    # Split testing
    percentage = models.IntegerField(default=50)  # Percentage of recipients

    # Statistics
    emails_sent = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)

    is_winner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['campaign', 'name']
        verbose_name = _('Campaign Variant')
        verbose_name_plural = _('Campaign Variants')
        db_table = 'campaign_variants'

    def __str__(self):
        return f'{self.campaign.name} - {self.name}'

    @property
    def open_rate(self):
        if self.emails_sent > 0:
            return (self.emails_opened / self.emails_sent) * 100
        return 0

    @property
    def click_rate(self):
        if self.emails_sent > 0:
            return (self.emails_clicked / self.emails_sent) * 100
        return 0