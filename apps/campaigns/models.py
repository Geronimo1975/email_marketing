from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.conf import settings
import uuid


class EmailTemplate(models.Model):
    """E-Mail Vorlagen für Reinigungsservice Kampagnen"""

    class TemplateType(models.TextChoices):
        WELCOME = 'welcome', 'Willkommen'
        NEWSLETTER = 'newsletter', 'Newsletter'
        PROMOTIONAL = 'promotional', 'Werbung'
        FOLLOW_UP = 'follow_up', 'Nachfass'
        QUOTE_REQUEST = 'quote', 'Angebot'
        SERVICE_REMINDER = 'reminder', 'Service Erinnerung'
        SEASONAL = 'seasonal', 'Saisonal'

    class TemplateKind(models.TextChoices):
        CAMPAIGN = 'campaign', 'Campaign'
        AUTOMATION = 'automation', 'Automation'

    class ServiceType(models.TextChoices):
        OFFICE_CLEANING = 'office', 'Büroreinigung'
        WINDOW_CLEANING = 'windows', 'Fensterreinigung'
        DEEP_CLEANING = 'deep', 'Grundreinigung'
        MAINTENANCE = 'maintenance', 'Unterhaltsreinigung'
        SPECIAL_CLEANING = 'special', 'Sonderreinigung'
        ALL_SERVICES = 'all', 'Alle Services'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Template Name")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    team = models.ForeignKey('accounts.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='email_templates', verbose_name="Team")
    template_type = models.CharField(max_length=20, choices=TemplateType.choices, default=TemplateType.NEWSLETTER, verbose_name="Template Typ")
    # Tests expect a field named 'type'
    type = models.CharField(max_length=20, choices=TemplateKind.choices, default=TemplateKind.CAMPAIGN, verbose_name="Typ")
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, default=ServiceType.ALL_SERVICES, verbose_name="Service Typ")

    # Template content
    subject = models.CharField(max_length=255, verbose_name="Betreff")
    from_name = models.CharField(max_length=100, default="North Cleaning Services", verbose_name="Absender Name")
    html_content = models.TextField(verbose_name="HTML Inhalt")
    text_content = models.TextField(blank=True, verbose_name="Text Inhalt")

    # Template metadata
    variables = JSONField(default=list, blank=True, help_text="Template Variablen wie {{first_name}}, {{company_name}}", verbose_name="Variablen")
    thumbnail = models.ImageField(
        upload_to='template_thumbnails/',
        blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg'])],
        verbose_name="Vorschaubild"
    )
    html_file = models.FileField(
        upload_to='template_files/',
        blank=True,
        validators=[FileExtensionValidator(['html'])],
        verbose_name="HTML Datei"
    )

    # Usage tracking
    times_used = models.PositiveIntegerField(default=0, verbose_name="Verwendungen")
    avg_open_rate = models.FloatField(default=0.0, verbose_name="Durchschnittliche Öffnungsrate")
    avg_click_rate = models.FloatField(default=0.0, verbose_name="Durchschnittliche Klickrate")

    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Erstellt von")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "E-Mail Template"
        verbose_name_plural = "E-Mail Templates"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def update_stats(self):
        """Update average rates from campaigns using this template"""
        campaigns = self.campaigns.filter(status='sent')
        if campaigns.exists():
            total_campaigns = campaigns.count()
            total_open_rate = sum(c.open_rate for c in campaigns)
            total_click_rate = sum(c.click_rate for c in campaigns)

            self.avg_open_rate = total_open_rate / total_campaigns
            self.avg_click_rate = total_click_rate / total_campaigns
            self.save()

    def save(self, *args, **kwargs):
        # Auto-assign team if not provided: use team where created_by is owner
        if self.team is None and self.created_by_id:
            try:
                from apps.accounts.models import Team
                owner_team = Team.objects.filter(owner_id=self.created_by_id).first()
                if owner_team:
                    self.team = owner_team
            except Exception:
                pass
        super().save(*args, **kwargs)


class EmailCampaign(models.Model):
    """E-Mail Marketing Kampagnen für Reinigungsservices"""

    class CampaignStatus(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        SCHEDULED = 'scheduled', 'Geplant'
        SENDING = 'sending', 'Wird gesendet'
        SENT = 'sent', 'Gesendet'
        PAUSED = 'paused', 'Pausiert'
        CANCELLED = 'cancelled', 'Abgebrochen'

    class CampaignType(models.TextChoices):
        REGULAR = 'regular', 'Regulär'
        AB_TEST = 'ab_test', 'A/B Test'
        FOLLOW_UP = 'follow_up', 'Nachfass'
        SEASONAL = 'seasonal', 'Saisonal'

    class Priority(models.TextChoices):
        LOW = 'low', 'Niedrig'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Hoch'
        URGENT = 'urgent', 'Dringend'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Kampagnen Name")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    campaign_type = models.CharField(max_length=20, choices=CampaignType.choices, default=CampaignType.REGULAR, verbose_name="Kampagnen Typ")
    # Tests expect a field named 'type'
    type = models.CharField(max_length=20, choices=CampaignType.choices, default=CampaignType.REGULAR, verbose_name="Typ")
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT, verbose_name="Status")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL, verbose_name="Priorität")

    # Email content
    subject = models.CharField(max_length=255, verbose_name="Betreff")
    from_email = models.EmailField(default="noreply@north-cleaning.de", verbose_name="Absender E-Mail")
    from_name = models.CharField(max_length=255, default="North Cleaning Services", verbose_name="Absender Name")
    reply_to = models.EmailField(blank=True, verbose_name="Antwort an")

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name="Template"
    )
    html_content = models.TextField(verbose_name="HTML Inhalt")
    text_content = models.TextField(blank=True, verbose_name="Text Inhalt")

    # Targeting - Hamburg cleaning services specific
    email_lists = models.ManyToManyField(
        'subscribers.EmailList',
        related_name='campaigns',
        verbose_name="E-Mail Listen"
    )
    target_business_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ziel Geschäftstypen",
        help_text="Liste der Business Types zu targeten"
    )
    target_districts = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ziel Bezirke",
        help_text="Hamburg Bezirke zu targeten"
    )

    # Scheduling (Europe/Berlin timezone)
    send_at = models.DateTimeField(null=True, blank=True, verbose_name="Senden am")
    timezone = models.CharField(max_length=50, default='Europe/Berlin', verbose_name="Zeitzone")

    # A/B Testing
    ab_test_percentage = models.IntegerField(default=100, verbose_name="A/B Test Prozent")
    ab_winner_criteria = models.CharField(
        max_length=50,
        blank=True,
        choices=[('open_rate', 'Öffnungsrate'), ('click_rate', 'Klickrate')],
        verbose_name="A/B Test Gewinner Kriterium"
    )
    ab_test_duration = models.IntegerField(default=24, verbose_name="A/B Test Dauer (Stunden)")

    # Tracking settings
    track_opens = models.BooleanField(default=True, verbose_name="Öffnungen verfolgen")
    track_clicks = models.BooleanField(default=True, verbose_name="Klicks verfolgen")

    # Statistics (denormalized for performance)
    total_recipients = models.IntegerField(default=0, verbose_name="Empfänger gesamt")
    emails_sent = models.IntegerField(default=0, verbose_name="E-Mails gesendet")
    emails_delivered = models.IntegerField(default=0, verbose_name="E-Mails zugestellt")
    emails_bounced = models.IntegerField(default=0, verbose_name="E-Mails bounced")
    emails_opened = models.IntegerField(default=0, verbose_name="E-Mails geöffnet")
    emails_clicked = models.IntegerField(default=0, verbose_name="E-Mails geklickt")
    unsubscribes = models.IntegerField(default=0, verbose_name="Abmeldungen")
    complaints = models.IntegerField(default=0, verbose_name="Beschwerden")

    # Business metrics for cleaning services
    quote_requests = models.IntegerField(default=0, verbose_name="Angebots-Anfragen")
    phone_calls = models.IntegerField(default=0, verbose_name="Anrufe")
    website_visits = models.IntegerField(default=0, verbose_name="Website Besuche")

    # Mailgun integration
    mailgun_campaign_id = models.CharField(max_length=255, blank=True, verbose_name="Mailgun Kampagnen ID")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Erstellt von")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")

    class Meta:
        verbose_name = "E-Mail Kampagne"
        verbose_name_plural = "E-Mail Kampagnen"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['send_at']),
            models.Index(fields=['campaign_type']),
            models.Index(fields=['mailgun_campaign_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def open_rate(self):
        if self.emails_delivered > 0:
            return round((self.emails_opened / self.emails_delivered) * 100, 2)
        return 0

    @property
    def click_rate(self):
        if self.emails_delivered > 0:
            return round((self.emails_clicked / self.emails_delivered) * 100, 2)
        return 0

    @property
    def bounce_rate(self):
        if self.emails_sent > 0:
            return round((self.emails_bounced / self.emails_sent) * 100, 2)
        return 0

    @property
    def conversion_rate(self):
        """Quote requests + phone calls as conversion"""
        if self.emails_delivered > 0:
            conversions = self.quote_requests + self.phone_calls
            return round((conversions / self.emails_delivered) * 100, 2)
        return 0

    def can_send(self):
        """Check if campaign can be sent"""
        return self.status in [self.CampaignStatus.DRAFT, self.CampaignStatus.SCHEDULED]

    def is_scheduled(self):
        """Check if campaign is scheduled for future sending"""
        return (
            self.status == self.CampaignStatus.SCHEDULED and
            self.send_at and
            self.send_at > timezone.now()
        )

    def get_target_contacts(self):
        """Get all contacts that match the targeting criteria"""
        from apps.subscribers.models import EmailContact

        contacts = EmailContact.objects.filter(
            is_active=True,
            is_subscribed=True,
            email_lists__in=self.email_lists.all()
        ).distinct()

        # Filter by business types if specified
        if self.target_business_types:
            contacts = contacts.filter(business_type__in=self.target_business_types)

        # Filter by Hamburg districts if specified
        if self.target_districts:
            contacts = contacts.filter(hamburg_district__in=self.target_districts)

        return contacts


class CampaignRecipient(models.Model):
    """Empfänger einer Kampagne mit Zustellungs-Tracking"""

    class RecipientStatus(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        SENT = 'sent', 'Gesendet'
        DELIVERED = 'delivered', 'Zugestellt'
        BOUNCED = 'bounced', 'Bounced'
        FAILED = 'failed', 'Fehlgeschlagen'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name="Kampagne"
    )
    contact = models.ForeignKey(
        'subscribers.EmailContact',
        on_delete=models.CASCADE,
        related_name='campaign_recipients',
        verbose_name="Kontakt"
    )

    status = models.CharField(
        max_length=20,
        choices=RecipientStatus.choices,
        default=RecipientStatus.PENDING,
        verbose_name="Status"
    )
    mailgun_message_id = models.CharField(max_length=255, blank=True, verbose_name="Mailgun Message ID")

    # Personalization data
    personalized_subject = models.CharField(max_length=255, blank=True, verbose_name="Personalisierter Betreff")
    personalized_content = models.TextField(blank=True, verbose_name="Personalisierter Inhalt")

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Gesendet am")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Zugestellt am")
    bounced_at = models.DateTimeField(null=True, blank=True, verbose_name="Bounced am")
    bounce_reason = models.TextField(blank=True, verbose_name="Bounce Grund")
    error_message = models.TextField(blank=True, verbose_name="Fehlermeldung")

    # Engagement tracking
    opened_at = models.DateTimeField(null=True, blank=True, verbose_name="Geöffnet am")
    clicked_at = models.DateTimeField(null=True, blank=True, verbose_name="Geklickt am")
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgemeldet am")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        unique_together = ['campaign', 'contact']
        verbose_name = "Kampagnen Empfänger"
        verbose_name_plural = "Kampagnen Empfänger"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['mailgun_message_id']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f'{self.campaign.name} -> {self.contact.email}'


class CampaignVariant(models.Model):
    """A/B Test Varianten für Kampagnen"""

    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name="Kampagne"
    )
    name = models.CharField(max_length=100, verbose_name="Varianten Name")
    description = models.TextField(blank=True, verbose_name="Beschreibung")

    # Variant content
    subject = models.CharField(max_length=255, verbose_name="Betreff")
    html_content = models.TextField(verbose_name="HTML Inhalt")
    text_content = models.TextField(blank=True, verbose_name="Text Inhalt")

    # Split testing
    percentage = models.IntegerField(default=50, verbose_name="Prozent der Empfänger")

    # Statistics
    emails_sent = models.IntegerField(default=0, verbose_name="E-Mails gesendet")
    emails_opened = models.IntegerField(default=0, verbose_name="E-Mails geöffnet")
    emails_clicked = models.IntegerField(default=0, verbose_name="E-Mails geklickt")
    conversions = models.IntegerField(default=0, verbose_name="Konversionen")

    is_winner = models.BooleanField(default=False, verbose_name="Gewinner")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        unique_together = ['campaign', 'name']
        verbose_name = "Kampagnen Variante"
        verbose_name_plural = "Kampagnen Varianten"

    def __str__(self):
        return f'{self.campaign.name} - {self.name}'

    @property
    def open_rate(self):
        if self.emails_sent > 0:
            return round((self.emails_opened / self.emails_sent) * 100, 2)
        return 0

    @property
    def click_rate(self):
        if self.emails_sent > 0:
            return round((self.emails_clicked / self.emails_sent) * 100, 2)
        return 0

    @property
    def conversion_rate(self):
        if self.emails_sent > 0:
            return round((self.conversions / self.emails_sent) * 100, 2)
        return 0


class CampaignSchedule(models.Model):
    """Zeitplanung für wiederkehrende Kampagnen"""

    class Frequency(models.TextChoices):
        ONCE = 'once', 'Einmalig'
        DAILY = 'daily', 'Täglich'
        WEEKLY = 'weekly', 'Wöchentlich'
        MONTHLY = 'monthly', 'Monatlich'
        QUARTERLY = 'quarterly', 'Vierteljährlich'

    campaign = models.OneToOneField(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name="Kampagne"
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.ONCE,
        verbose_name="Häufigkeit"
    )
    start_date = models.DateTimeField(verbose_name="Start Datum")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="End Datum")

    # For weekly/monthly scheduling
    day_of_week = models.IntegerField(null=True, blank=True, verbose_name="Wochentag")  # 0=Monday, 6=Sunday
    day_of_month = models.IntegerField(null=True, blank=True, verbose_name="Tag des Monats")

    # For time-based scheduling
    send_time = models.TimeField(verbose_name="Sendezeit")
    timezone = models.CharField(max_length=50, default='Europe/Berlin', verbose_name="Zeitzone")

    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    last_run = models.DateTimeField(null=True, blank=True, verbose_name="Letzte Ausführung")
    next_run = models.DateTimeField(null=True, blank=True, verbose_name="Nächste Ausführung")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Kampagnen Zeitplan"
        verbose_name_plural = "Kampagnen Zeitpläne"

    def __str__(self):
        return f"{self.campaign.name} - {self.get_frequency_display()}"

# Backwards-compatibility aliases for tests
# Tests import `Campaign` and expect related names/types from an older schema.
Campaign = EmailCampaign