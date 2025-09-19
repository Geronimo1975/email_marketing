from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.validators import EmailValidator
from django.utils import timezone
from django.conf import settings
import uuid


class EmailList(models.Model):
    """Segmented contact lists for email campaigns"""

    class ListType(models.TextChoices):
        PROSPECTS = 'prospects', 'Interessenten'
        CUSTOMERS = 'customers', 'Kunden'
        LEADS = 'leads', 'Leads'
        NEWSLETTER = 'newsletter', 'Newsletter'
        CUSTOM = 'custom', 'Benutzerdefiniert'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Listenname")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    list_type = models.CharField(max_length=20, choices=ListType.choices, default=ListType.PROSPECTS, verbose_name="Listentyp")
    team = models.ForeignKey('accounts.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriber_lists', verbose_name="Team")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Erstellt von")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    class Meta:
        verbose_name = "E-Mail Liste"
        verbose_name_plural = "E-Mail Listen"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_list_type_display()})"

    @property
    def contact_count(self):
        return self.contacts.filter(is_active=True).count()

    @property
    def subscribed_count(self):
        return self.contacts.filter(is_active=True, is_subscribed=True).count()


class EmailContact(models.Model):
    """Individual contacts with business information for Hamburg cleaning services"""

    class BusinessType(models.TextChoices):
        OFFICE_BUILDING = 'office', 'Bürogebäude'
        RETAIL_STORE = 'retail', 'Einzelhandel'
        RESTAURANT = 'restaurant', 'Gastronomie'
        MEDICAL_PRACTICE = 'medical', 'Arztpraxis'
        SCHOOL = 'school', 'Bildungseinrichtung'
        WAREHOUSE = 'warehouse', 'Lager/Logistik'
        HOTEL = 'hotel', 'Hotel/Beherbergung'
        APARTMENT_COMPLEX = 'apartment', 'Wohnanlage'
        MANUFACTURING = 'manufacturing', 'Produktion'
        FITNESS_CENTER = 'fitness', 'Fitnessstudio'
        OTHER = 'other', 'Sonstige'

    class HamburgDistrict(models.TextChoices):
        ALTONA = 'altona', 'Altona'
        BERGEDORF = 'bergedorf', 'Bergedorf'
        EIMSBUETTEL = 'eimsbuettel', 'Eimsbüttel'
        HARBURG = 'harburg', 'Harburg'
        HAMBURG_MITTE = 'mitte', 'Hamburg-Mitte'
        HAMBURG_NORD = 'nord', 'Hamburg-Nord'
        WANDSBEK = 'wandsbek', 'Wandsbek'
        OUTSIDE_HAMBURG = 'outside', 'Außerhalb Hamburg'

    class Size(models.TextChoices):
        SMALL = 'small', 'Klein (< 500m²)'
        MEDIUM = 'medium', 'Mittel (500-2000m²)'
        LARGE = 'large', 'Groß (2000-5000m²)'
        XLARGE = 'xlarge', 'Sehr groß (> 5000m²)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[EmailValidator()], verbose_name="E-Mail")
    first_name = models.CharField(max_length=100, verbose_name="Vorname")
    last_name = models.CharField(max_length=100, verbose_name="Nachname")
    company_name = models.CharField(max_length=255, verbose_name="Firmenname")
    position = models.CharField(max_length=100, blank=True, verbose_name="Position")

    # Business details
    business_type = models.CharField(max_length=20, choices=BusinessType.choices, verbose_name="Geschäftstyp")
    company_size = models.CharField(max_length=10, choices=Size.choices, blank=True, verbose_name="Betriebsgröße")
    hamburg_district = models.CharField(max_length=20, choices=HamburgDistrict.choices, default=HamburgDistrict.HAMBURG_MITTE, verbose_name="Hamburger Bezirk")
    address = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    website = models.URLField(blank=True, verbose_name="Website")

    # Email marketing fields
    email_lists = models.ManyToManyField(EmailList, related_name='subscribers', blank=True, verbose_name="E-Mail Listen")
    is_subscribed = models.BooleanField(default=True, verbose_name="Abonniert")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    # GDPR compliance
    gdpr_consent = models.BooleanField(default=False, verbose_name="DSGVO Einverständnis")
    consent_date = models.DateTimeField(default=timezone.now, verbose_name="Einverständnis vom")
    consent_source = models.CharField(max_length=100, blank=True, verbose_name="Einverständnis Quelle")
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgemeldet am")

    # Engagement tracking
    emails_sent = models.PositiveIntegerField(default=0, verbose_name="E-Mails gesendet")
    emails_opened = models.PositiveIntegerField(default=0, verbose_name="E-Mails geöffnet")
    emails_clicked = models.PositiveIntegerField(default=0, verbose_name="E-Mails geklickt")
    last_opened = models.DateTimeField(null=True, blank=True, verbose_name="Zuletzt geöffnet")
    last_clicked = models.DateTimeField(null=True, blank=True, verbose_name="Zuletzt geklickt")
    engagement_score = models.FloatField(default=0.0, verbose_name="Engagement Score")

    # Lead scoring for cleaning services
    has_current_service = models.BooleanField(default=False, verbose_name="Hat aktuellen Reinigungsservice")
    current_service_provider = models.CharField(max_length=255, blank=True, verbose_name="Aktueller Anbieter")
    contract_end_date = models.DateField(null=True, blank=True, verbose_name="Vertragsende")
    interested_services = models.JSONField(default=list, blank=True, verbose_name="Interessierte Services")
    budget_range = models.CharField(max_length=50, blank=True, verbose_name="Budget Bereich")

    # CRM integration
    odoo_contact_id = models.IntegerField(null=True, blank=True, verbose_name="Odoo Kontakt ID")

    # Metadata
    source = models.CharField(max_length=100, blank=True, help_text="Website, Messe, Empfehlung, etc.", verbose_name="Quelle")
    notes = models.TextField(blank=True, verbose_name="Notizen")
    language = models.CharField(max_length=10, default='de', verbose_name="Sprache")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "E-Mail Kontakt"
        verbose_name_plural = "E-Mail Kontakte"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['business_type']),
            models.Index(fields=['hamburg_district']),
            models.Index(fields=['engagement_score']),
            models.Index(fields=['odoo_contact_id']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.company_name}) - {self.email}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def open_rate(self):
        if self.emails_sent == 0:
            return 0
        return round((self.emails_opened / self.emails_sent) * 100, 2)

    @property
    def click_rate(self):
        if self.emails_sent == 0:
            return 0
        return round((self.emails_clicked / self.emails_sent) * 100, 2)

    @property
    def is_hot_lead(self):
        """Determine if this is a hot lead based on engagement and business data"""
        criteria = 0
        if self.engagement_score > 0.7:
            criteria += 1
        if self.contract_end_date and self.contract_end_date <= timezone.now().date() + timezone.timedelta(days=90):
            criteria += 2
        if not self.has_current_service:
            criteria += 1
        if self.business_type in ['office', 'retail', 'medical']:
            criteria += 1
        return criteria >= 3

    def unsubscribe(self):
        """Unsubscribe contact from all lists"""
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save()

    def resubscribe(self):
        """Resubscribe contact"""
        self.is_subscribed = True
        self.unsubscribed_at = None
        self.save()


class ContactImport(models.Model):
    """Track CSV import operations"""

    class ImportStatus(models.TextChoices):
        PENDING = 'pending', 'Ausstehend'
        PROCESSING = 'processing', 'Wird verarbeitet'
        COMPLETED = 'completed', 'Abgeschlossen'
        FAILED = 'failed', 'Fehlgeschlagen'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, verbose_name="Dateiname")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Hochgeladen von")
    email_list = models.ForeignKey(EmailList, on_delete=models.CASCADE, verbose_name="Ziel-Liste")
    status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING, verbose_name="Status")

    # Statistics
    total_rows = models.PositiveIntegerField(default=0, verbose_name="Gesamte Zeilen")
    successful_imports = models.PositiveIntegerField(default=0, verbose_name="Erfolgreich importiert")
    failed_imports = models.PositiveIntegerField(default=0, verbose_name="Fehlgeschlagen")
    duplicates_skipped = models.PositiveIntegerField(default=0, verbose_name="Duplikate übersprungen")

    # Error tracking
    error_log = models.TextField(blank=True, verbose_name="Fehler-Log")
    processed_file = models.FileField(upload_to='imports/', blank=True, verbose_name="Verarbeitete Datei")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Abgeschlossen am")

    class Meta:
        verbose_name = "Kontakt Import"
        verbose_name_plural = "Kontakt Imports"
        ordering = ['-created_at']

    def __str__(self):
        return f"Import: {self.filename} ({self.get_status_display()})"

    @property
    def success_rate(self):
        if self.total_rows == 0:
            return 0
        return round((self.successful_imports / self.total_rows) * 100, 2)


class Tag(models.Model):
    """Tags for organizing and segmenting subscribers"""

    name = models.CharField(max_length=100, verbose_name="Tag Name")
    color = models.CharField(max_length=7, default='#007bff', verbose_name="Farbe")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    team = models.ForeignKey('accounts.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='tags', verbose_name="Team")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name

# Backwards compatibility: some modules import ContactTag
ContactTag = Tag


class ContactNote(models.Model):
    """Notes and interactions with contacts"""

    contact = models.ForeignKey(EmailContact, on_delete=models.CASCADE, related_name='contact_notes', verbose_name="Kontakt")
    note = models.TextField(verbose_name="Notiz")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Erstellt von")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    is_important = models.BooleanField(default=False, verbose_name="Wichtig")

    class Meta:
        verbose_name = "Kontakt Notiz"
        verbose_name_plural = "Kontakt Notizen"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notiz für {self.contact.full_name} - {self.created_at.strftime('%d.%m.%Y')}"


# Add many-to-many relationship for tags
EmailContact.add_to_class('tags', models.ManyToManyField(Tag, blank=True, related_name='subscribers', verbose_name="Tags"))


class SegmentRule(models.Model):
    """Rules for segmenting subscribers"""

    OPERATORS = [
        ('equals', 'Equals'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts with'),
        ('ends_with', 'Ends with'),
        ('is_empty', 'Is empty'),
        ('is_not_empty', 'Is not empty'),
        ('greater_than', 'Greater than'),
        ('less_than', 'Less than'),
        ('date_after', 'Date after'),
        ('date_before', 'Date before'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    team = models.ForeignKey('accounts.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='segment_rules')
    field = models.CharField(max_length=50)
    operator = models.CharField(max_length=20, choices=OPERATORS)
    value = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class Subscription(models.Model):
    """Subscription relation between subscriber and list"""

    class Status(models.TextChoices):
        SUBSCRIBED = 'subscribed', 'Subscribed'
        UNSUBSCRIBED = 'unsubscribed', 'Unsubscribed'

    subscriber = models.ForeignKey(EmailContact, on_delete=models.CASCADE, related_name='subscriptions')
    subscriber_list = models.ForeignKey(EmailList, on_delete=models.CASCADE, related_name='subscriptions')
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBSCRIBED)
    created_at = models.DateTimeField(auto_now_add=True)

# Backwards-compatibility aliases expected by tests
Subscriber = EmailContact
SubscriberList = EmailList