"""
Integration services for external APIs.
"""

import requests
import hmac
import hashlib
import json
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class MailgunService:
    """Service for interacting with Mailgun API."""

    def __init__(self, api_key: str = None, domain: str = None):
        self.api_key = api_key or settings.MAILGUN_API_KEY
        self.domain = domain or settings.MAILGUN_DOMAIN
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}"

        if not self.api_key or not self.domain:
            raise ValueError("Mailgun API key and domain must be configured")

    def _make_request(self, method: str, endpoint: str, data: Dict = None,
                     files: Dict = None) -> Dict:
        """Make authenticated request to Mailgun API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        auth = ('api', self.api_key)

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=auth,
                data=data,
                files=files,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Mailgun API error: {e}")
            raise

    def send_email(self, to_email: str, subject: str, html_content: str,
                   text_content: str = None, from_email: str = None,
                   from_name: str = None, tags: List[str] = None,
                   custom_vars: Dict = None, track_opens: bool = True,
                   track_clicks: bool = True) -> Dict:
        """Send individual email via Mailgun."""

        from_address = from_email or f"noreply@{self.domain}"
        if from_name:
            from_address = f"{from_name} <{from_address}>"

        data = {
            'from': from_address,
            'to': to_email,
            'subject': subject,
            'html': html_content,
        }

        if text_content:
            data['text'] = text_content

        if tags:
            data['o:tag'] = tags

        if custom_vars:
            for key, value in custom_vars.items():
                data[f'v:{key}'] = value

        # Tracking settings
        data['o:tracking'] = 'yes' if track_opens else 'no'
        data['o:tracking-clicks'] = 'yes' if track_clicks else 'no'
        data['o:tracking-opens'] = 'yes' if track_opens else 'no'

        return self._make_request('POST', 'messages', data=data)

    def send_bulk_email(self, recipients: List[Dict], subject: str,
                       html_content: str, text_content: str = None,
                       from_email: str = None, from_name: str = None,
                       tags: List[str] = None, track_opens: bool = True,
                       track_clicks: bool = True) -> Dict:
        """Send bulk email with recipient variables."""

        from_address = from_email or f"noreply@{self.domain}"
        if from_name:
            from_address = f"{from_name} <{from_address}>"

        # Extract email addresses and recipient variables
        to_emails = [r['email'] for r in recipients]
        recipient_vars = {r['email']: r.get('vars', {}) for r in recipients}

        data = {
            'from': from_address,
            'to': to_emails,
            'subject': subject,
            'html': html_content,
            'recipient-variables': json.dumps(recipient_vars),
        }

        if text_content:
            data['text'] = text_content

        if tags:
            data['o:tag'] = tags

        # Tracking settings
        data['o:tracking'] = 'yes' if track_opens else 'no'
        data['o:tracking-clicks'] = 'yes' if track_clicks else 'no'
        data['o:tracking-opens'] = 'yes' if track_opens else 'no'

        return self._make_request('POST', 'messages', data=data)

    def validate_email(self, email: str) -> Dict:
        """Validate email address using Mailgun validation API."""
        url = "https://api.mailgun.net/v4/address/validate"
        auth = ('api', self.api_key)

        response = requests.get(
            url,
            auth=auth,
            params={'address': email},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_suppressions(self, suppression_type: str = 'bounces') -> List[Dict]:
        """Get suppression list (bounces, unsubscribes, complaints)."""
        endpoint = f"/{suppression_type}"
        response = self._make_request('GET', endpoint)
        return response.get('items', [])

    def add_to_suppression(self, email: str, suppression_type: str = 'bounces',
                          reason: str = None) -> Dict:
        """Add email to suppression list."""
        endpoint = f"/{suppression_type}"
        data = {'address': email}
        if reason:
            data['reason'] = reason

        return self._make_request('POST', endpoint, data=data)

    def remove_from_suppression(self, email: str,
                               suppression_type: str = 'bounces') -> bool:
        """Remove email from suppression list."""
        endpoint = f"/{suppression_type}/{email}"
        try:
            self._make_request('DELETE', endpoint)
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False  # Email not in suppression list
            raise

    def verify_webhook_signature(self, timestamp: str, token: str,
                                signature: str) -> bool:
        """Verify Mailgun webhook signature."""
        signing_key = settings.MAILGUN_WEBHOOK_SIGNING_KEY
        if not signing_key:
            logger.warning("Mailgun webhook signing key not configured")
            return False

        expected_signature = hmac.new(
            key=signing_key.encode(),
            msg=f'{timestamp}{token}'.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def get_events(self, begin: str = None, end: str = None,
                   event_type: str = None, limit: int = 300) -> List[Dict]:
        """Get email events from Mailgun."""
        params = {'limit': limit}

        if begin:
            params['begin'] = begin
        if end:
            params['end'] = end
        if event_type:
            params['event'] = event_type

        url = f"{self.base_url}/events"
        auth = ('api', self.api_key)

        response = requests.get(url, auth=auth, params=params, timeout=30)
        response.raise_for_status()

        return response.json().get('items', [])


class OdooService:
    """Service for interacting with Odoo CRM API."""

    def __init__(self, url: str = None, username: str = None,
                 api_key: str = None, database: str = None):
        self.url = (url or settings.ODOO_URL).rstrip('/')
        self.username = username or settings.ODOO_USERNAME
        self.api_key = api_key or settings.ODOO_API_KEY
        self.database = database or getattr(settings, 'ODOO_DATABASE', 'odoo')

        if not all([self.url, self.username, self.api_key]):
            raise ValueError("Odoo URL, username, and API key must be configured")

    def _authenticate(self) -> int:
        """Authenticate with Odoo and return user ID."""
        try:
            import xmlrpc.client

            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            uid = common.authenticate(
                self.database, self.username, self.api_key, {}
            )

            if not uid:
                raise ValueError("Authentication failed")

            return uid
        except Exception as e:
            logger.error(f"Odoo authentication error: {e}")
            raise

    def _make_request(self, model: str, method: str, *args, **kwargs) -> Any:
        """Make authenticated request to Odoo."""
        import xmlrpc.client

        uid = self._authenticate()
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

        try:
            return models.execute_kw(
                self.database, uid, self.api_key,
                model, method, args, kwargs
            )
        except Exception as e:
            logger.error(f"Odoo API error: {e}")
            raise

    def search_contacts(self, domain: List = None, limit: int = None) -> List[int]:
        """Search for contacts in Odoo."""
        domain = domain or []
        kwargs = {}
        if limit:
            kwargs['limit'] = limit

        return self._make_request('res.partner', 'search', domain, **kwargs)

    def get_contacts(self, contact_ids: List[int] = None,
                    fields: List[str] = None) -> List[Dict]:
        """Get contact details from Odoo."""
        if contact_ids is None:
            contact_ids = self.search_contacts()

        fields = fields or [
            'name', 'email', 'phone', 'mobile', 'street', 'city',
            'state_id', 'country_id', 'zip', 'category_id', 'is_company',
            'create_date', 'write_date'
        ]

        return self._make_request('res.partner', 'read', contact_ids, fields)

    def create_contact(self, contact_data: Dict) -> int:
        """Create new contact in Odoo."""
        return self._make_request('res.partner', 'create', contact_data)

    def update_contact(self, contact_id: int, update_data: Dict) -> bool:
        """Update existing contact in Odoo."""
        return self._make_request(
            'res.partner', 'write', [contact_id], update_data
        )

    def sync_email_engagement(self, contact_id: int, engagement_data: Dict):
        """Update contact with email engagement data."""
        # This would typically use custom fields in Odoo
        update_data = {
            'x_email_engagement_score': engagement_data.get('engagement_score', 0),
            'x_last_email_opened': engagement_data.get('last_opened'),
            'x_total_emails_opened': engagement_data.get('emails_opened', 0),
            'x_total_emails_clicked': engagement_data.get('emails_clicked', 0),
        }

        return self.update_contact(contact_id, update_data)

    def get_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact by email address."""
        domain = [('email', '=', email)]
        contact_ids = self.search_contacts(domain, limit=1)

        if contact_ids:
            contacts = self.get_contacts(contact_ids)
            return contacts[0] if contacts else None

        return None


def validate_webhook_signature(request, provider: str) -> bool:
    """Validate webhook signature based on provider."""
    if provider == 'mailgun':
        timestamp = request.POST.get('timestamp')
        token = request.POST.get('token')
        signature = request.POST.get('signature')

        if not all([timestamp, token, signature]):
            return False

        mailgun_service = MailgunService()
        return mailgun_service.verify_webhook_signature(timestamp, token, signature)

    # Add other providers as needed
    return False


def process_mailgun_webhook(webhook_data: Dict) -> bool:
    """Process Mailgun webhook data and create email events."""
    from apps.analytics.models import EmailEvent
    from apps.subscribers.models import Subscriber

    try:
        event_data = webhook_data.get('event-data', {})
        event_type = event_data.get('event')

        if not event_type:
            logger.warning("No event type in webhook data")
            return False

        # Map Mailgun events to our event types
        event_mapping = {
            'delivered': EmailEvent.EventType.DELIVERED,
            'opened': EmailEvent.EventType.OPENED,
            'clicked': EmailEvent.EventType.CLICKED,
            'unsubscribed': EmailEvent.EventType.UNSUBSCRIBED,
            'complained': EmailEvent.EventType.COMPLAINED,
            'bounced': EmailEvent.EventType.BOUNCED,
            'failed': EmailEvent.EventType.FAILED,
        }

        mapped_event_type = event_mapping.get(event_type)
        if not mapped_event_type:
            logger.info(f"Unsupported event type: {event_type}")
            return False

        # Extract common fields
        recipient_email = event_data.get('recipient')
        timestamp = timezone.datetime.fromtimestamp(
            event_data.get('timestamp', 0), tz=timezone.utc
        )

        # Create email event
        event = EmailEvent.objects.create(
            event_type=mapped_event_type,
            timestamp=timestamp,
            mailgun_message_id=event_data.get('message', {}).get('headers', {}).get('message-id', ''),
            mailgun_event_id=event_data.get('id', ''),
            recipient_email=recipient_email,
            url=event_data.get('url', ''),
            user_agent=event_data.get('client-info', {}).get('user-agent', ''),
            ip_address=event_data.get('ip', ''),
            device_type=event_data.get('client-info', {}).get('device-type', ''),
            client_name=event_data.get('client-info', {}).get('client-name', ''),
            client_os=event_data.get('client-info', {}).get('client-os', ''),
            country=event_data.get('geolocation', {}).get('country', ''),
            region=event_data.get('geolocation', {}).get('region', ''),
            city=event_data.get('geolocation', {}).get('city', ''),
            bounce_reason=event_data.get('reason', ''),
            error_message=event_data.get('delivery-status', {}).get('description', ''),
            raw_data=webhook_data
        )

        # Try to link to subscriber
        try:
            subscriber = Subscriber.objects.get(email=recipient_email)
            event.subscriber = subscriber
            event.save()
        except Subscriber.DoesNotExist:
            logger.info(f"Subscriber not found for email: {recipient_email}")

        return True

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return False