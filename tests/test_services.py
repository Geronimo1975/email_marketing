"""
Comprehensive service and integration tests for Email Marketing Platform.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException, HTTPError

from apps.integrations.services import (
    MailgunService,
    OdooService,
    validate_webhook_signature,
    process_mailgun_webhook,
)


class TestMailgunService(TestCase):
    """Test Mailgun service functionality."""

    def setUp(self):
        self.mailgun_service = MailgunService(
            api_key="test-api-key", domain="test.example.com"
        )

    def test_mailgun_service_initialization(self):
        """Test Mailgun service initialization."""
        service = MailgunService(api_key="test-api-key", domain="test.example.com")
        self.assertEqual(service.api_key, "test-api-key")
        self.assertEqual(service.domain, "test.example.com")
        self.assertEqual(
            service.base_url, "https://api.mailgun.net/v3/test.example.com"
        )

    def test_mailgun_service_initialization_with_settings(self):
        """Test Mailgun service initialization with settings."""
        with patch.object(settings, "MAILGUN_API_KEY", "settings-api-key"):
            with patch.object(settings, "MAILGUN_DOMAIN", "settings.example.com"):
                service = MailgunService()
                self.assertEqual(service.api_key, "settings-api-key")
                self.assertEqual(service.domain, "settings.example.com")

    def test_mailgun_service_initialization_missing_credentials(self):
        """Test Mailgun service initialization with missing credentials."""
        with patch.object(settings, "MAILGUN_API_KEY", ""):
            with patch.object(settings, "MAILGUN_DOMAIN", ""):
                with self.assertRaises(ValueError):
                    MailgunService()

    @patch("requests.request")
    def test_make_request_success(self, mock_request):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"message": "success"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = self.mailgun_service._make_request("GET", "test-endpoint")
        self.assertEqual(result, {"message": "success"})
        mock_request.assert_called_once()

    @patch("requests.request")
    def test_make_request_failure(self, mock_request):
        """Test failed API request."""
        mock_request.side_effect = RequestException("API Error")

        with self.assertRaises(RequestException):
            self.mailgun_service._make_request("GET", "test-endpoint")

    @patch("requests.request")
    def test_send_email(self, mock_request):
        """Test send email functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "test-message-id"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = self.mailgun_service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
        )

        self.assertEqual(result, {"id": "test-message-id"})
        mock_request.assert_called_once()

    @patch("requests.request")
    def test_send_bulk_email(self, mock_request):
        """Test send bulk email functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "test-bulk-id"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        recipients = [
            {"email": "test1@example.com", "vars": {"first_name": "John"}},
            {"email": "test2@example.com", "vars": {"first_name": "Jane"}},
        ]

        result = self.mailgun_service.send_bulk_email(
            recipients=recipients,
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
        )

        self.assertEqual(result, {"id": "test-bulk-id"})
        mock_request.assert_called_once()

    @patch("requests.get")
    def test_validate_email(self, mock_get):
        """Test email validation functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "is_valid": True,
            "reason": "Valid email",
            "risk": "low",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.mailgun_service.validate_email("test@example.com")
        expected_result = {"is_valid": True, "reason": "Valid email", "risk": "low"}
        self.assertEqual(result, expected_result)

    @patch("requests.get")
    def test_get_suppressions(self, mock_get):
        """Test get suppressions functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [{"address": "bounced@example.com", "reason": "hard_bounce"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.mailgun_service.get_suppressions("bounces")
        expected_result = [{"address": "bounced@example.com", "reason": "hard_bounce"}]
        self.assertEqual(result, expected_result)

    @patch("requests.post")
    def test_add_to_suppression(self, mock_post):
        """Test add to suppression functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {"message": "Added to suppression list"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.mailgun_service.add_to_suppression(
            "bounced@example.com", "bounces", "hard_bounce"
        )
        expected_result = {"message": "Added to suppression list"}
        self.assertEqual(result, expected_result)

    @patch("requests.delete")
    def test_remove_from_suppression_success(self, mock_delete):
        """Test remove from suppression success."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_delete.return_value = mock_response

        result = self.mailgun_service.remove_from_suppression(
            "bounced@example.com", "bounces"
        )
        self.assertTrue(result)

    @patch("requests.delete")
    def test_remove_from_suppression_not_found(self, mock_delete):
        """Test remove from suppression not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_delete.side_effect = HTTPError(response=mock_response)
        mock_delete.return_value = mock_response

        result = self.mailgun_service.remove_from_suppression(
            "bounced@example.com", "bounces"
        )
        self.assertFalse(result)

    def test_verify_webhook_signature(self):
        """Test webhook signature verification."""
        with patch.object(settings, "MAILGUN_WEBHOOK_SIGNING_KEY", "test-signing-key"):
            import hmac
            import hashlib

            timestamp = "1640995200"
            token = "test-token"
            signature = hmac.new(
                "test-signing-key".encode(),
                f"{timestamp}{token}".encode(),
                hashlib.sha256,
            ).hexdigest()

            result = self.mailgun_service.verify_webhook_signature(
                timestamp, token, signature
            )
            self.assertTrue(result)

    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        with patch.object(settings, "MAILGUN_WEBHOOK_SIGNING_KEY", "test-signing-key"):
            result = self.mailgun_service.verify_webhook_signature(
                "1640995200", "test-token", "invalid-signature"
            )
            self.assertFalse(result)

    def test_verify_webhook_signature_missing_key(self):
        """Test webhook signature verification with missing signing key."""
        with patch.object(settings, "MAILGUN_WEBHOOK_SIGNING_KEY", ""):
            result = self.mailgun_service.verify_webhook_signature(
                "1640995200", "test-token", "signature"
            )
            self.assertFalse(result)

    @patch("requests.get")
    def test_get_events(self, mock_get):
        """Test get events functionality."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"event": "opened", "timestamp": 1640995200},
                {"event": "clicked", "timestamp": 1640995201},
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.mailgun_service.get_events(
            begin="2024-01-01", end="2024-01-31", event_type="opened"
        )
        expected_result = [
            {"event": "opened", "timestamp": 1640995200},
            {"event": "clicked", "timestamp": 1640995201},
        ]
        self.assertEqual(result, expected_result)


class TestOdooService(TestCase):
    """Test Odoo service functionality."""

    def setUp(self):
        self.odoo_service = OdooService(
            url="https://test.odoo.com",
            username="testuser",
            api_key="test-api-key",
            database="test_db",
        )

    def test_odoo_service_initialization(self):
        """Test Odoo service initialization."""
        service = OdooService(
            url="https://test.odoo.com",
            username="testuser",
            api_key="test-api-key",
            database="test_db",
        )
        self.assertEqual(service.url, "https://test.odoo.com")
        self.assertEqual(service.username, "testuser")
        self.assertEqual(service.api_key, "test-api-key")
        self.assertEqual(service.database, "test_db")

    def test_odoo_service_initialization_with_settings(self):
        """Test Odoo service initialization with settings."""
        with patch.object(settings, "ODOO_URL", "https://settings.odoo.com"):
            with patch.object(settings, "ODOO_USERNAME", "settingsuser"):
                with patch.object(settings, "ODOO_API_KEY", "settings-key"):
                    service = OdooService()
                    self.assertEqual(service.url, "https://settings.odoo.com")
                    self.assertEqual(service.username, "settingsuser")
                    self.assertEqual(service.api_key, "settings-key")

    def test_odoo_service_initialization_missing_credentials(self):
        """Test Odoo service initialization with missing credentials."""
        with patch.object(settings, "ODOO_URL", ""):
            with patch.object(settings, "ODOO_USERNAME", ""):
                with patch.object(settings, "ODOO_API_KEY", ""):
                    with self.assertRaises(ValueError):
                        OdooService()

    @patch("xmlrpc.client.ServerProxy")
    def test_authenticate_success(self, mock_server_proxy):
        """Test successful authentication."""
        mock_common = Mock()
        mock_common.authenticate.return_value = 1
        mock_server_proxy.return_value = mock_common

        result = self.odoo_service._authenticate()
        self.assertEqual(result, 1)

    @patch("xmlrpc.client.ServerProxy")
    def test_authenticate_failure(self, mock_server_proxy):
        """Test failed authentication."""
        mock_common = Mock()
        mock_common.authenticate.return_value = False
        mock_server_proxy.return_value = mock_common

        with self.assertRaises(ValueError):
            self.odoo_service._authenticate()

    @patch("xmlrpc.client.ServerProxy")
    def test_authenticate_exception(self, mock_server_proxy):
        """Test authentication with exception."""
        mock_server_proxy.side_effect = Exception("Connection error")

        with self.assertRaises(Exception):
            self.odoo_service._authenticate()

    @patch("xmlrpc.client.ServerProxy")
    def test_make_request_success(self, mock_server_proxy):
        """Test successful API request."""
        mock_common = Mock()
        mock_common.authenticate.return_value = 1
        mock_models = Mock()
        mock_models.execute_kw.return_value = [1, 2, 3]
        mock_server_proxy.side_effect = [mock_common, mock_models]

        result = self.odoo_service._make_request("res.partner", "search", [])
        self.assertEqual(result, [1, 2, 3])

    @patch("xmlrpc.client.ServerProxy")
    def test_make_request_failure(self, mock_server_proxy):
        """Test failed API request."""
        mock_common = Mock()
        mock_common.authenticate.return_value = 1
        mock_models = Mock()
        mock_models.execute_kw.side_effect = Exception("API Error")
        mock_server_proxy.side_effect = [mock_common, mock_models]

        with self.assertRaises(Exception):
            self.odoo_service._make_request("res.partner", "search", [])

    @patch.object(OdooService, "_make_request")
    def test_search_contacts(self, mock_make_request):
        """Test search contacts functionality."""
        mock_make_request.return_value = [1, 2, 3]

        result = self.odoo_service.search_contacts(
            domain=[("email", "=", "test@example.com")]
        )
        self.assertEqual(result, [1, 2, 3])
        mock_make_request.assert_called_once_with(
            "res.partner", "search", [("email", "=", "test@example.com")]
        )

    @patch.object(OdooService, "_make_request")
    def test_get_contacts(self, mock_make_request):
        """Test get contacts functionality."""
        mock_make_request.return_value = [
            {"id": 1, "name": "Test Contact", "email": "test@example.com"}
        ]

        result = self.odoo_service.get_contacts([1, 2, 3])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Test Contact")

    @patch.object(OdooService, "_make_request")
    def test_create_contact(self, mock_make_request):
        """Test create contact functionality."""
        mock_make_request.return_value = 1

        contact_data = {
            "name": "New Contact",
            "email": "new@example.com",
            "is_company": False,
        }

        result = self.odoo_service.create_contact(contact_data)
        self.assertEqual(result, 1)
        mock_make_request.assert_called_once_with("res.partner", "create", contact_data)

    @patch.object(OdooService, "_make_request")
    def test_update_contact(self, mock_make_request):
        """Test update contact functionality."""
        mock_make_request.return_value = True

        update_data = {"name": "Updated Contact", "email": "updated@example.com"}

        result = self.odoo_service.update_contact(1, update_data)
        self.assertTrue(result)
        mock_make_request.assert_called_once_with(
            "res.partner", "write", [1], update_data
        )

    @patch.object(OdooService, "_make_request")
    def test_sync_email_engagement(self, mock_make_request):
        """Test sync email engagement functionality."""
        mock_make_request.return_value = True

        engagement_data = {
            "engagement_score": 0.8,
            "last_opened": "2024-01-01",
            "emails_opened": 10,
            "emails_clicked": 5,
        }

        result = self.odoo_service.sync_email_engagement(1, engagement_data)
        self.assertTrue(result)

    @patch.object(OdooService, "search_contacts")
    @patch.object(OdooService, "get_contacts")
    def test_get_contact_by_email_found(self, mock_get_contacts, mock_search_contacts):
        """Test get contact by email when contact is found."""
        mock_search_contacts.return_value = [1]
        mock_get_contacts.return_value = [
            {"id": 1, "name": "Test Contact", "email": "test@example.com"}
        ]

        result = self.odoo_service.get_contact_by_email("test@example.com")
        self.assertEqual(result["name"], "Test Contact")

    @patch.object(OdooService, "search_contacts")
    def test_get_contact_by_email_not_found(self, mock_search_contacts):
        """Test get contact by email when contact is not found."""
        mock_search_contacts.return_value = []

        result = self.odoo_service.get_contact_by_email("test@example.com")
        self.assertIsNone(result)


class TestWebhookFunctions(TestCase):
    """Test webhook utility functions."""

    def test_validate_webhook_signature_mailgun(self):
        """Test validate webhook signature for Mailgun."""
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = Mock()
            mock_service.verify_webhook_signature.return_value = True
            mock_service_class.return_value = mock_service

            # Mock request object
            request = Mock()
            request.POST = {
                "timestamp": "1640995200",
                "token": "test-token",
                "signature": "test-signature",
            }

            result = validate_webhook_signature(request, "mailgun")
            self.assertTrue(result)

    def test_validate_webhook_signature_unsupported_provider(self):
        """Test validate webhook signature for unsupported provider."""
        request = Mock()
        result = validate_webhook_signature(request, "unsupported")
        self.assertFalse(result)

    def test_validate_webhook_signature_missing_data(self):
        """Test validate webhook signature with missing data."""
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = Mock()
            mock_service.verify_webhook_signature.return_value = False
            mock_service_class.return_value = mock_service

            # Mock request object with missing data
            request = Mock()
            request.POST = {}

            result = validate_webhook_signature(request, "mailgun")
            self.assertFalse(result)

    @patch("apps.analytics.models.EmailEvent.objects.create")
    @patch("apps.subscribers.models.Subscriber.objects.get")
    def test_process_mailgun_webhook_success(
        self, mock_get_subscriber, mock_create_event
    ):
        """Test successful webhook processing."""
        mock_subscriber = Mock()
        mock_subscriber.email = "test@example.com"
        mock_get_subscriber.return_value = mock_subscriber

        mock_event = Mock()
        mock_create_event.return_value = mock_event

        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
                "message": {"headers": {"message-id": "test-message-id"}},
                "client-info": {
                    "user-agent": "Mozilla/5.0 (Test Browser)",
                    "device-type": "desktop",
                    "client-name": "Test Client",
                    "client-os": "Test OS",
                },
                "geolocation": {
                    "country": "US",
                    "region": "CA",
                    "city": "San Francisco",
                },
            }
        }

        result = process_mailgun_webhook(webhook_data)
        self.assertTrue(result)
        mock_create_event.assert_called_once()

    @patch("apps.analytics.models.EmailEvent.objects.create")
    def test_process_mailgun_webhook_no_event_type(self, mock_create_event):
        """Test webhook processing with no event type."""
        webhook_data = {
            "event-data": {
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
            }
        }

        result = process_mailgun_webhook(webhook_data)
        self.assertFalse(result)
        mock_create_event.assert_not_called()

    @patch("apps.analytics.models.EmailEvent.objects.create")
    def test_process_mailgun_webhook_unsupported_event(self, mock_create_event):
        """Test webhook processing with unsupported event type."""
        webhook_data = {
            "event-data": {
                "event": "unsupported_event",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
            }
        }

        result = process_mailgun_webhook(webhook_data)
        self.assertFalse(result)
        mock_create_event.assert_not_called()

    @patch("apps.analytics.models.EmailEvent.objects.create")
    @patch("apps.subscribers.models.Subscriber.objects.get")
    def test_process_mailgun_webhook_subscriber_not_found(
        self, mock_get_subscriber, mock_create_event
    ):
        """Test webhook processing when subscriber is not found."""
        from apps.subscribers.models import Subscriber

        mock_get_subscriber.side_effect = Subscriber.DoesNotExist()

        mock_event = Mock()
        mock_create_event.return_value = mock_event

        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
                "message": {"headers": {"message-id": "test-message-id"}},
            }
        }

        result = process_mailgun_webhook(webhook_data)
        self.assertTrue(result)
        mock_create_event.assert_called_once()

    @patch("apps.analytics.models.EmailEvent.objects.create")
    def test_process_mailgun_webhook_exception(self, mock_create_event):
        """Test webhook processing with exception."""
        mock_create_event.side_effect = Exception("Database error")

        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
                "message": {"headers": {"message-id": "test-message-id"}},
            }
        }

        result = process_mailgun_webhook(webhook_data)
        self.assertFalse(result)


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestServiceIntegration:
    """Test service integration with models."""

    def test_mailgun_service_with_campaign(self, campaign, mock_mailgun_service):
        """Test Mailgun service integration with campaign."""
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service_class.return_value = mock_mailgun_service

            service = MailgunService()
            result = service.send_email(
                to_email="test@example.com",
                subject=campaign.subject,
                html_content=campaign.html_content,
            )

            assert result["id"] == "test-message-id"
            mock_mailgun_service.send_email.assert_called_once()

    def test_odoo_service_with_subscriber(self, subscriber, mock_odoo_service):
        """Test Odoo service integration with subscriber."""
        with patch("apps.integrations.services.OdooService") as mock_service_class:
            mock_service_class.return_value = mock_odoo_service

            service = OdooService()
            result = service.create_contact(
                {
                    "name": subscriber.full_name,
                    "email": subscriber.email,
                    "is_company": False,
                }
            )

            assert result == 1
            mock_odoo_service.create_contact.assert_called_once()

    def test_webhook_processing_with_models(self, subscriber, campaign):
        """Test webhook processing with existing models."""
        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": subscriber.email,
                "message": {"headers": {"message-id": "test-message-id"}},
            }
        }

        result = process_mailgun_webhook(webhook_data)
        assert result is True

        # Check that EmailEvent was created
        from apps.analytics.models import EmailEvent

        event = EmailEvent.objects.get(mailgun_event_id="test-event-id")
        assert event.recipient_email == subscriber.email
        assert event.event_type == "opened"


@pytest.mark.django_db
class TestServiceErrorHandling:
    """Test service error handling."""

    def test_mailgun_service_network_error(self):
        """Test Mailgun service network error handling."""
        with patch("requests.request") as mock_request:
            mock_request.side_effect = RequestException("Network error")

            service = MailgunService("test-key", "test.com")
            with pytest.raises(RequestException):
                service.send_email(
                    to_email="test@example.com",
                    subject="Test",
                    html_content="<h1>Test</h1>",
                )

    def test_odoo_service_authentication_error(self):
        """Test Odoo service authentication error handling."""
        with patch("xmlrpc.client.ServerProxy") as mock_server_proxy:
            mock_common = Mock()
            mock_common.authenticate.return_value = False
            mock_server_proxy.return_value = mock_common

            service = OdooService("https://test.com", "user", "key", "db")
            with pytest.raises(ValueError):
                service._authenticate()

    def test_webhook_processing_error(self):
        """Test webhook processing error handling."""
        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": "invalid-timestamp",  # Invalid timestamp
                "recipient": "test@example.com",
            }
        }

        result = process_mailgun_webhook(webhook_data)
        assert result is False


@pytest.mark.django_db
class TestServiceConfiguration:
    """Test service configuration and settings."""

    def test_mailgun_service_configuration(self):
        """Test Mailgun service configuration."""
        with patch.object(settings, "MAILGUN_API_KEY", "test-key"):
            with patch.object(settings, "MAILGUN_DOMAIN", "test.com"):
                service = MailgunService()
                assert service.api_key == "test-key"
                assert service.domain == "test.com"

    def test_odoo_service_configuration(self):
        """Test Odoo service configuration."""
        with patch.object(settings, "ODOO_URL", "https://test.com"):
            with patch.object(settings, "ODOO_USERNAME", "user"):
                with patch.object(settings, "ODOO_API_KEY", "key"):
                    service = OdooService()
                    assert service.url == "https://test.com"
                    assert service.username == "user"
                    assert service.api_key == "key"

    def test_webhook_signature_verification_configuration(self):
        """Test webhook signature verification configuration."""
        with patch.object(settings, "MAILGUN_WEBHOOK_SIGNING_KEY", "test-key"):
            service = MailgunService()
            result = service.verify_webhook_signature(
                "1640995200", "token", "signature"
            )
            # Should not raise exception even with invalid signature
            assert isinstance(result, bool)
