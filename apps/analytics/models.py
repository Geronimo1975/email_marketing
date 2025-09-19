from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.utils import timezone
from django.contrib.auth.models import User
import uuid


class EmailEvent(models.Model):
    """E-Mail Events von Mailgun Webhooks verfolgen"""

    class EventType(models.TextChoices):
        DELIVERED = 'delivered', 'Zugestellt'
        OPENED = 'opened', 'Geöffnet'
        CLICKED = 'clicked', 'Geklickt'
        UNSUBSCRIBED = 'unsubscribed', 'Abgemeldet'
        COMPLAINED = 'complained', 'Beschwerde'
        BOUNCED = 'bounced', 'Bounced'
        FAILED = 'failed', 'Fehlgeschlagen'

    # Core event data
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=20, choices=EventType.choices, verbose_name="Event Typ")
    timestamp = models.DateTimeField(verbose_name="Zeitstempel")

    # Message identification
    mailgun_message_id = models.CharField(max_length=255, db_index=True, verbose_name="Mailgun Message ID")
    mailgun_event_id = models.CharField(max_length=255, unique=True, verbose_name="Mailgun Event ID")

    # Recipient information
    recipient_email = models.EmailField(db_index=True, verbose_name="Empfänger E-Mail")
    contact = models.ForeignKey(
        'subscribers.EmailContact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_events',
        verbose_name="Kontakt"
    )

    # Campaign information
    campaign = models.ForeignKey(
        'campaigns.EmailCampaign',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_events',
        verbose_name="Kampagne"
    )
    campaign_recipient = models.ForeignKey(
        'campaigns.CampaignRecipient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_events',
        verbose_name="Kampagnen Empfänger"
    )

    # Event-specific data for cleaning business
    url = models.URLField(blank=True, verbose_name="URL")  # For click events
    link_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('quote_request', 'Angebot anfordern'),
            ('phone_call', 'Anrufen'),
            ('website', 'Website'),
            ('service_info', 'Service Info'),
            ('contact', 'Kontakt'),
            ('unsubscribe', 'Abmelden'),
            ('other', 'Sonstige')
        ],
        verbose_name="Link Typ"
    )

    # Device/Client information
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Adresse")
    device_type = models.CharField(max_length=50, blank=True, verbose_name="Gerät Typ")
    client_name = models.CharField(max_length=100, blank=True, verbose_name="E-Mail Client")
    client_os = models.CharField(max_length=100, blank=True, verbose_name="Betriebssystem")

    # Bounce/failure specific
    bounce_reason = models.TextField(blank=True, verbose_name="Bounce Grund")
    bounce_code = models.CharField(max_length=10, blank=True, verbose_name="Bounce Code")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")

    # Geolocation data (especially relevant for Hamburg area)
    country = models.CharField(max_length=100, blank=True, verbose_name="Land")
    region = models.CharField(max_length=100, blank=True, verbose_name="Region")
    city = models.CharField(max_length=100, blank=True, verbose_name="Stadt")

    # Business context for cleaning services
    business_hour = models.BooleanField(default=False, verbose_name="Geschäftszeit")  # Was it during business hours?
    is_mobile_device = models.BooleanField(default=False, verbose_name="Mobil Gerät")

    # Raw webhook data
    raw_data = JSONField(default=dict, blank=True, verbose_name="Rohdaten")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "E-Mail Event"
        verbose_name_plural = "E-Mail Events"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['campaign', 'event_type']),
            models.Index(fields=['contact', 'event_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['link_type']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.recipient_email} - {self.timestamp.strftime("%d.%m.%Y %H:%M")}'

    def save(self, *args, **kwargs):
        # Determine if event happened during business hours (9 AM - 6 PM, Monday-Friday)
        if self.timestamp:
            weekday = self.timestamp.weekday()  # 0=Monday, 6=Sunday
            hour = self.timestamp.hour
            self.business_hour = weekday < 5 and 9 <= hour <= 18

        # Determine if mobile device
        if self.user_agent:
            mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
            self.is_mobile_device = any(keyword in self.user_agent.lower() for keyword in mobile_keywords)

        super().save(*args, **kwargs)


class CampaignReport(models.Model):
    """Tägliche Kampagnen Performance Berichte"""

    campaign = models.ForeignKey(
        'campaigns.EmailCampaign',
        on_delete=models.CASCADE,
        related_name='daily_reports',
        verbose_name="Kampagne"
    )
    date = models.DateField(verbose_name="Datum")

    # Email counts
    emails_sent = models.IntegerField(default=0, verbose_name="E-Mails gesendet")
    emails_delivered = models.IntegerField(default=0, verbose_name="E-Mails zugestellt")
    emails_bounced = models.IntegerField(default=0, verbose_name="E-Mails bounced")
    emails_failed = models.IntegerField(default=0, verbose_name="E-Mails fehlgeschlagen")

    # Engagement counts
    unique_opens = models.IntegerField(default=0, verbose_name="Eindeutige Öffnungen")
    total_opens = models.IntegerField(default=0, verbose_name="Öffnungen gesamt")
    unique_clicks = models.IntegerField(default=0, verbose_name="Eindeutige Klicks")
    total_clicks = models.IntegerField(default=0, verbose_name="Klicks gesamt")

    # Business-specific metrics for cleaning services
    quote_request_clicks = models.IntegerField(default=0, verbose_name="Angebot-Klicks")
    phone_call_clicks = models.IntegerField(default=0, verbose_name="Anruf-Klicks")
    website_visits = models.IntegerField(default=0, verbose_name="Website Besuche")

    # Time-based analytics
    business_hour_opens = models.IntegerField(default=0, verbose_name="Öffnungen Geschäftszeit")
    mobile_opens = models.IntegerField(default=0, verbose_name="Mobile Öffnungen")

    # Negative actions
    unsubscribes = models.IntegerField(default=0, verbose_name="Abmeldungen")
    complaints = models.IntegerField(default=0, verbose_name="Beschwerden")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        unique_together = ['campaign', 'date']
        verbose_name = "Kampagnen Bericht"
        verbose_name_plural = "Kampagnen Berichte"
        ordering = ['-date']

    def __str__(self):
        return f'{self.campaign.name} - {self.date.strftime("%d.%m.%Y")}'

    @property
    def open_rate(self):
        if self.emails_delivered > 0:
            return round((self.unique_opens / self.emails_delivered) * 100, 2)
        return 0

    @property
    def click_rate(self):
        if self.emails_delivered > 0:
            return round((self.unique_clicks / self.emails_delivered) * 100, 2)
        return 0

    @property
    def bounce_rate(self):
        if self.emails_sent > 0:
            return round((self.emails_bounced / self.emails_sent) * 100, 2)
        return 0

    @property
    def business_conversion_rate(self):
        """Rate of business-relevant clicks (quotes + phone calls)"""
        if self.emails_delivered > 0:
            business_clicks = self.quote_request_clicks + self.phone_call_clicks
            return round((business_clicks / self.emails_delivered) * 100, 2)
        return 0

    @property
    def mobile_engagement_rate(self):
        """Percentage of opens from mobile devices"""
        if self.unique_opens > 0:
            return round((self.mobile_opens / self.unique_opens) * 100, 2)
        return 0


class ContactActivity(models.Model):
    """Kontakt Engagement über alle Kampagnen verfolgen"""

    contact = models.OneToOneField(
        'subscribers.EmailContact',
        on_delete=models.CASCADE,
        related_name='activity_summary',
        verbose_name="Kontakt"
    )

    # Email counts
    emails_received = models.IntegerField(default=0, verbose_name="E-Mails erhalten")
    emails_opened = models.IntegerField(default=0, verbose_name="E-Mails geöffnet")
    emails_clicked = models.IntegerField(default=0, verbose_name="E-Mails geklickt")

    # Business-specific engagement for cleaning services
    quote_requests = models.IntegerField(default=0, verbose_name="Angebots-Anfragen")
    phone_clicks = models.IntegerField(default=0, verbose_name="Anruf-Klicks")
    service_page_visits = models.IntegerField(default=0, verbose_name="Service Seiten Besuche")

    # Engagement timing
    first_opened = models.DateTimeField(null=True, blank=True, verbose_name="Erste Öffnung")
    last_opened = models.DateTimeField(null=True, blank=True, verbose_name="Letzte Öffnung")
    first_clicked = models.DateTimeField(null=True, blank=True, verbose_name="Erster Klick")
    last_clicked = models.DateTimeField(null=True, blank=True, verbose_name="Letzter Klick")

    # Calculated scores
    engagement_score = models.FloatField(default=0.0, verbose_name="Engagement Score")
    lead_score = models.FloatField(default=0.0, verbose_name="Lead Score")

    # Behavioral data specific to Hamburg cleaning business
    preferred_send_time = models.TimeField(null=True, blank=True, verbose_name="Bevorzugte Sendezeit")
    preferred_day_of_week = models.IntegerField(null=True, blank=True, verbose_name="Bevorzugter Wochentag")  # 0=Monday
    most_interested_service = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('office', 'Büroreinigung'),
            ('windows', 'Fensterreinigung'),
            ('deep', 'Grundreinigung'),
            ('maintenance', 'Unterhaltsreinigung'),
            ('special', 'Sonderreinigung')
        ],
        verbose_name="Meist interessierter Service"
    )

    # Device preferences
    primarily_mobile = models.BooleanField(default=False, verbose_name="Hauptsächlich mobil")
    prefers_business_hours = models.BooleanField(default=True, verbose_name="Bevorzugt Geschäftszeiten")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Kontakt Aktivität"
        verbose_name_plural = "Kontakt Aktivitäten"

    def __str__(self):
        return f'Aktivität: {self.contact.email}'

    @property
    def open_rate(self):
        if self.emails_received > 0:
            return round((self.emails_opened / self.emails_received) * 100, 2)
        return 0

    @property
    def click_rate(self):
        if self.emails_received > 0:
            return round((self.emails_clicked / self.emails_received) * 100, 2)
        return 0

    @property
    def business_engagement_rate(self):
        """Rate of business-relevant actions"""
        if self.emails_received > 0:
            business_actions = self.quote_requests + self.phone_clicks
            return round((business_actions / self.emails_received) * 100, 2)
        return 0

    def update_lead_score(self):
        """Calculate lead score based on engagement and business actions"""
        score = 0

        # Engagement component (40%)
        if self.engagement_score > 0:
            score += self.engagement_score * 40

        # Business actions component (60%)
        business_actions = self.quote_requests + self.phone_clicks
        if business_actions > 0:
            score += min(business_actions * 10, 60)

        # Contact profile bonus
        if hasattr(self.contact, 'is_hot_lead') and self.contact.is_hot_lead:
            score += 20

        self.lead_score = min(score, 100)
        self.save(update_fields=['lead_score'])

# Backwards compatibility alias for tests
SubscriberActivity = ContactActivity


class LinkClick(models.Model):
    """Aggregated link click metrics per campaign and URL."""

    campaign = models.ForeignKey(
        'campaigns.EmailCampaign',
        on_delete=models.CASCADE,
        related_name='link_clicks',
        verbose_name="Kampagne",
    )
    url = models.URLField()
    click_count = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    last_clicked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['campaign', 'url']
        indexes = [
            models.Index(fields=['campaign']),
            models.Index(fields=['url']),
        ]


class DomainReputation(models.Model):
    """Reputation metrics for sending domains."""

    domain = models.CharField(max_length=255, unique=True)
    reputation_score = models.FloatField(default=0.0)
    delivery_rate = models.FloatField(default=0.0)
    bounce_rate = models.FloatField(default=0.0)
    complaint_rate = models.FloatField(default=0.0)
    last_checked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['domain']),
        ]


class HamburgBusinessReport(models.Model):
    """Spezielle Berichte für Hamburg Reinigungsservice Business"""

    date = models.DateField(verbose_name="Datum")

    # Business metrics by district
    altona_contacts = models.IntegerField(default=0, verbose_name="Altona Kontakte")
    bergedorf_contacts = models.IntegerField(default=0, verbose_name="Bergedorf Kontakte")
    eimsbuettel_contacts = models.IntegerField(default=0, verbose_name="Eimsbüttel Kontakte")
    harburg_contacts = models.IntegerField(default=0, verbose_name="Harburg Kontakte")
    mitte_contacts = models.IntegerField(default=0, verbose_name="Hamburg-Mitte Kontakte")
    nord_contacts = models.IntegerField(default=0, verbose_name="Hamburg-Nord Kontakte")
    wandsbek_contacts = models.IntegerField(default=0, verbose_name="Wandsbek Kontakte")

    # Business type engagement
    office_engagement = models.FloatField(default=0.0, verbose_name="Büro Engagement Rate")
    retail_engagement = models.FloatField(default=0.0, verbose_name="Einzelhandel Engagement Rate")
    medical_engagement = models.FloatField(default=0.0, verbose_name="Arztpraxis Engagement Rate")
    restaurant_engagement = models.FloatField(default=0.0, verbose_name="Gastronomie Engagement Rate")

    # Lead generation metrics
    total_quote_requests = models.IntegerField(default=0, verbose_name="Angebots-Anfragen gesamt")
    total_phone_calls = models.IntegerField(default=0, verbose_name="Anrufe gesamt")
    hot_leads_generated = models.IntegerField(default=0, verbose_name="Hot Leads generiert")

    # Time-based insights
    best_send_hour = models.IntegerField(null=True, blank=True, verbose_name="Beste Sendezeit (Stunde)")
    best_send_day = models.IntegerField(null=True, blank=True, verbose_name="Bester Sendetag")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "Hamburg Business Bericht"
        verbose_name_plural = "Hamburg Business Berichte"
        ordering = ['-date']

    def __str__(self):
        return f"Hamburg Business Report - {self.date.strftime('%d.%m.%Y')}"

    @property
    def total_district_contacts(self):
        return (self.altona_contacts + self.bergedorf_contacts + self.eimsbuettel_contacts +
                self.harburg_contacts + self.mitte_contacts + self.nord_contacts + self.wandsbek_contacts)

    @property
    def conversion_rate(self):
        """Overall conversion rate for business actions"""
        if self.total_district_contacts > 0:
            conversions = self.total_quote_requests + self.total_phone_calls
            return round((conversions / self.total_district_contacts) * 100, 2)
        return 0