"""
German-specific validators for Hamburg cleaning services email marketing
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import gettext as _


class GermanEmailValidator(EmailValidator):
    """Enhanced email validator for German business emails"""

    message = _('Geben Sie eine gültige E-Mail-Adresse ein.')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Common German business domains
        self.german_business_domains = {
            '.de', '.com', '.eu', '.org', '.net',
            # German-specific business domains
            '.gmbh', '.ag', '.kg', '.ohg', '.eg'
        }

    def __call__(self, value):
        # First run standard email validation
        super().__call__(value)

        # Additional checks for German business context
        if value:
            self._validate_german_business_email(value)

    def _validate_german_business_email(self, email):
        """Additional validation for German business emails"""
        domain = email.split('@')[-1].lower()

        # Warn about suspicious domains (but don't block)
        suspicious_domains = [
            'example.com', 'test.com', 'fake.com', 'dummy.com',
            'temp-mail.org', '10minutemail.com', 'guerrillamail.com'
        ]

        if any(suspicious in domain for suspicious in suspicious_domains):
            raise ValidationError(
                _('Diese E-Mail-Adresse scheint nicht für Geschäftszwecke geeignet zu sein.')
            )


class HamburgPostalCodeValidator:
    """Validator for Hamburg postal codes"""

    message = _('Geben Sie eine gültige Hamburger Postleitzahl ein (20095-22769).')

    def __call__(self, value):
        if not value:
            return

        # Remove spaces and ensure string
        postal_code = str(value).replace(' ', '')

        # Hamburg postal codes range from 20095 to 22769
        if not re.match(r'^2[0-2]\d{3}$', postal_code):
            raise ValidationError(self.message)

        postal_int = int(postal_code)
        if not (20095 <= postal_int <= 22769):
            raise ValidationError(self.message)


class GermanPhoneValidator:
    """Validator for German phone numbers"""

    message = _('Geben Sie eine gültige deutsche Telefonnummer ein.')

    def __call__(self, value):
        if not value:
            return

        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(value))

        # German phone number patterns
        patterns = [
            r'^\+49\d{10,11}$',  # +49 followed by 10-11 digits
            r'^0\d{9,11}$',      # 0 followed by 9-11 digits (domestic)
            r'^\d{10,12}$',      # 10-12 digits (international without +)
        ]

        if not any(re.match(pattern, cleaned) for pattern in patterns):
            raise ValidationError(self.message)


class BusinessNameValidator:
    """Validator for German business names"""

    message = _('Geben Sie einen gültigen Firmennamen ein.')

    def __call__(self, value):
        if not value:
            raise ValidationError(_('Firmenname ist erforderlich.'))

        # Minimum length
        if len(value.strip()) < 2:
            raise ValidationError(_('Firmenname muss mindestens 2 Zeichen lang sein.'))

        # Check for suspicious patterns
        suspicious_patterns = [
            r'^test\s*$',
            r'^example\s*$',
            r'^dummy\s*$',
            r'^\d+$',  # Only numbers
            r'^[^a-zA-ZäöüÄÖÜß]+$',  # No letters at all
        ]

        for pattern in suspicious_patterns:
            if re.match(pattern, value.strip(), re.IGNORECASE):
                raise ValidationError(
                    _('Bitte geben Sie einen echten Firmennamen ein.')
                )


class GDPRConsentValidator:
    """Validator for GDPR consent requirements"""

    def __call__(self, value):
        if not value:
            raise ValidationError(
                _('Die Zustimmung zur Datenverarbeitung gemäß DSGVO ist erforderlich.')
            )


def validate_hamburg_district(value):
    """Validate Hamburg district selection"""
    valid_districts = [
        'altona', 'bergedorf', 'eimsbuettel', 'harburg',
        'mitte', 'nord', 'wandsbek', 'outside'
    ]

    if value not in valid_districts:
        raise ValidationError(
            _('Bitte wählen Sie einen gültigen Hamburger Bezirk aus.')
        )


def validate_business_type(value):
    """Validate business type for cleaning services"""
    valid_types = [
        'office', 'retail', 'restaurant', 'medical', 'school',
        'warehouse', 'hotel', 'apartment', 'manufacturing',
        'fitness', 'other'
    ]

    if value not in valid_types:
        raise ValidationError(
            _('Bitte wählen Sie einen gültigen Geschäftstyp aus.')
        )


def validate_cleaning_service_interest(services):
    """Validate interested cleaning services"""
    if not services:
        return

    valid_services = [
        'office_cleaning', 'window_cleaning', 'deep_cleaning',
        'maintenance_cleaning', 'special_cleaning', 'carpet_cleaning',
        'floor_care', 'facade_cleaning'
    ]

    if isinstance(services, list):
        for service in services:
            if service not in valid_services:
                raise ValidationError(
                    _('Unbekannter Service: {service}').format(service=service)
    elif isinstance(services, str):
        # Handle comma-separated string
        service_list = [s.strip() for s in services.split(',')]
        for service in service_list:
            if service and service not in valid_services:
                raise ValidationError(
                    _('Unbekannter Service: {service}').format(service=service)


class ContractEndDateValidator:
    """Validator for contract end dates in business context"""

    def __call__(self, value):
        if not value:
            return

        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()

        # Contract end date should not be in the far past
        if value < today - timedelta(days=365):
            raise ValidationError(
                _('Das Vertragsende liegt zu weit in der Vergangenheit.')
            )

        # Contract end date should not be too far in future
        if value > today + timedelta(days=365 * 5):
            raise ValidationError(
                _('Das Vertragsende liegt zu weit in der Zukunft.')
            )


def validate_budget_range(value):
    """Validate budget range for cleaning services"""
    if not value:
        return

    valid_ranges = [
        'unter_500', '500_1000', '1000_2500', '2500_5000',
        '5000_10000', 'ueber_10000', 'nach_vereinbarung'
    ]

    if value not in valid_ranges:
        raise ValidationError(
            _('Bitte wählen Sie eine gültige Budget-Kategorie aus.')
        )


class EmailTemplateValidator:
    """Validator for email template content"""

    def __call__(self, value):
        if not value:
            raise ValidationError(_('Template-Inhalt ist erforderlich.'))

        # Check for required elements in German templates
        required_elements = ['{{first_name}}', '{{company_name}}']
        missing_elements = []

        for element in required_elements:
            if element not in value:
                missing_elements.append(element)

        if missing_elements:
            raise ValidationError(
                _('Folgende Template-Variablen fehlen: {}').format(
                    ', '.join(missing_elements)
                )
            )

        # Check for GDPR compliance elements
        gdpr_elements = ['datenschutz', 'abmelden', 'unsubscribe']
        has_gdpr = any(element.lower() in value.lower() for element in gdpr_elements)

        if not has_gdpr:
            raise ValidationError(
                _('Das Template muss DSGVO-konforme Elemente enthalten (Datenschutz/Abmelden).')
            )


def validate_mailgun_webhook_signature(timestamp, token, signature):
    """Validate Mailgun webhook signature for security"""
    import hmac
    import hashlib
    from django.conf import settings

    if not all([timestamp, token, signature]):
        raise ValidationError(_('Unvollständige Webhook-Signatur.'))

    signing_key = getattr(settings, 'MAILGUN_WEBHOOK_SIGNING_KEY', '')
    if not signing_key:
        raise ValidationError(_('Mailgun Webhook Signing Key nicht konfiguriert.'))

    expected_signature = hmac.new(
        key=signing_key.encode(),
        msg=f'{timestamp}{token}'.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise ValidationError(_('Ungültige Webhook-Signatur.'))

    return True