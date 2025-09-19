"""
Pytest configuration and fixtures for Email Marketing Platform tests.
"""

import pytest
import os
import django
from django.conf import settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.management import call_command
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
django.setup()

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup test database for the entire test session."""
    with django_db_blocker.unblock():
        call_command("migrate", verbosity=0, interactive=False)


@pytest.fixture
def db_access(request):
    """Ensure database access for tests."""
    pass


@pytest.fixture
def user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "password": "testpass123",
        "role": "admin",
        "company_name": "Test Company",
        "phone_number": "+1234567890",
        "timezone": "UTC",
        "is_email_verified": True,
    }


@pytest.fixture
def user(user_data):
    """Create a test user."""
    return User.objects.create_user(**user_data)


@pytest.fixture
def team(user):
    """Create a test team."""
    from apps.accounts.models import Team

    return Team.objects.create(
        name="Test Team", description="Test team description", owner=user
    )


@pytest.fixture
def subscriber_data():
    """Sample subscriber data for testing."""
    return {
        "email": "subscriber@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "status": "subscribed",
        "custom_fields": {"company": "Test Corp", "industry": "Technology"},
        "timezone": "UTC",
        "preferred_language": "en",
        "gdpr_consent": True,
        "gdpr_consent_date": datetime.now(),
        "is_active": True,
    }


@pytest.fixture
def subscriber(subscriber_data, team):
    """Create a test subscriber."""
    from apps.subscribers.models import Subscriber

    subscriber = Subscriber.objects.create(**subscriber_data)
    subscriber.team = team
    subscriber.save()
    return subscriber


@pytest.fixture
def subscriber_list(team, user):
    """Create a test subscriber list."""
    from apps.subscribers.models import SubscriberList

    return SubscriberList.objects.create(
        name="Test List", description="Test subscriber list", team=team, created_by=user
    )


@pytest.fixture
def email_template(team, user):
    """Create a test email template."""
    from apps.campaigns.models import EmailTemplate

    return EmailTemplate.objects.create(
        name="Test Template",
        description="Test email template",
        type="campaign",
        team=team,
        subject="Test Subject",
        html_content="<h1>Test HTML Content</h1>",
        text_content="Test Text Content",
        variables=["first_name", "last_name"],
        created_by=user,
    )


@pytest.fixture
def campaign(team, user, email_template, subscriber_list):
    """Create a test campaign."""
    from apps.campaigns.models import Campaign

    campaign = Campaign.objects.create(
        name="Test Campaign",
        description="Test campaign description",
        type="regular",
        status="draft",
        team=team,
        subject="Test Campaign Subject",
        from_email="test@example.com",
        from_name="Test Sender",
        reply_to="reply@example.com",
        template=email_template,
        html_content="<h1>Test Campaign HTML</h1>",
        text_content="Test Campaign Text",
        timezone="UTC",
        track_opens=True,
        track_clicks=True,
        created_by=user,
    )
    campaign.subscriber_lists.add(subscriber_list)
    return campaign


@pytest.fixture
def automation_workflow(team, user):
    """Create a test automation workflow."""
    from apps.automation.models import AutomationWorkflow

    return AutomationWorkflow.objects.create(
        name="Test Workflow",
        description="Test automation workflow",
        status="active",
        team=team,
        trigger_type="subscriber_added",
        trigger_config={"list_id": 1},
        entry_conditions=[],
        exit_conditions=[],
        allow_re_entry=False,
        max_entries_per_subscriber=1,
        created_by=user,
    )


@pytest.fixture
def workflow_step(automation_workflow, email_template):
    """Create a test workflow step."""
    from apps.automation.models import WorkflowStep

    return WorkflowStep.objects.create(
        workflow=automation_workflow,
        name="Test Step",
        step_type="email",
        order=1,
        config={"template_id": email_template.id, "subject": "Test Email"},
        email_template=email_template,
        is_active=True,
    )


@pytest.fixture
def email_event(campaign, subscriber):
    """Create a test email event."""
    from apps.analytics.models import EmailEvent

    return EmailEvent.objects.create(
        event_type="opened",
        timestamp=datetime.now(),
        mailgun_message_id="test-message-id-123",
        mailgun_event_id="test-event-id-123",
        recipient_email=subscriber.email,
        subscriber=subscriber,
        campaign=campaign,
        user_agent="Mozilla/5.0 (Test Browser)",
        ip_address="192.168.1.1",
        device_type="desktop",
        client_name="Test Client",
        client_os="Test OS",
        country="US",
        region="CA",
        city="San Francisco",
        raw_data={"test": "data"},
    )


@pytest.fixture
def integration(team, user):
    """Create a test integration."""
    from apps.integrations.models import Integration

    return Integration.objects.create(
        name="Test Mailgun Integration",
        provider="mailgun",
        status="active",
        team=team,
        config={"domain": "test.example.com"},
        credentials='{"api_key": "test-key"}',
        is_active=True,
        created_by=user,
    )


@pytest.fixture
def webhook_endpoint(integration):
    """Create a test webhook endpoint."""
    from apps.integrations.models import WebhookEndpoint

    return WebhookEndpoint.objects.create(
        name="Test Mailgun Webhook",
        event_type="mailgun_delivery",
        url_path="test-mailgun-webhook",
        integration=integration,
        secret_key="test-secret-key",
        verify_signature=True,
        is_active=True,
        max_retries=3,
        retry_delay=60,
    )


@pytest.fixture
def mock_mailgun_service():
    """Mock Mailgun service for testing."""
    with patch("apps.integrations.services.MailgunService") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.send_email.return_value = {"id": "test-message-id"}
        mock_instance.send_bulk_email.return_value = {"id": "test-bulk-id"}
        mock_instance.validate_email.return_value = {"is_valid": True}
        mock_instance.get_suppressions.return_value = []
        mock_instance.add_to_suppression.return_value = {"message": "Added"}
        mock_instance.remove_from_suppression.return_value = True
        mock_instance.verify_webhook_signature.return_value = True
        mock_instance.get_events.return_value = []
        yield mock_instance


@pytest.fixture
def mock_odoo_service():
    """Mock Odoo service for testing."""
    with patch("apps.integrations.services.OdooService") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance._authenticate.return_value = 1
        mock_instance.search_contacts.return_value = [1, 2, 3]
        mock_instance.get_contacts.return_value = [
            {"id": 1, "name": "Test Contact", "email": "test@example.com"}
        ]
        mock_instance.create_contact.return_value = 1
        mock_instance.update_contact.return_value = True
        mock_instance.get_contact_by_email.return_value = {
            "id": 1,
            "name": "Test Contact",
            "email": "test@example.com",
        }
        yield mock_instance


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution."""
    with patch("celery.app.task.Task.delay") as mock:
        mock.return_value = MagicMock(id="test-task-id")
        yield mock


@pytest.fixture
def api_client():
    """Django REST Framework test client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user):
    """Authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for import testing."""
    return """email,first_name,last_name,company,industry
john@example.com,John,Doe,Acme Corp,Technology
jane@example.com,Jane,Smith,Tech Inc,Software
bob@example.com,Bob,Johnson,Data Co,Analytics"""


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
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
            "geolocation": {"country": "US", "region": "CA", "city": "San Francisco"},
        }
    }


@pytest.fixture
def sample_campaign_data():
    """Sample campaign data for testing."""
    return {
        "name": "Test Campaign",
        "description": "Test campaign description",
        "type": "regular",
        "status": "draft",
        "subject": "Test Campaign Subject",
        "from_email": "test@example.com",
        "from_name": "Test Sender",
        "reply_to": "reply@example.com",
        "html_content": "<h1>Test Campaign HTML</h1>",
        "text_content": "Test Campaign Text",
        "timezone": "UTC",
        "track_opens": True,
        "track_clicks": True,
        "subscriber_lists": [1],
    }


@pytest.fixture
def sample_subscriber_data():
    """Sample subscriber data for testing."""
    return {
        "email": "newsubscriber@example.com",
        "first_name": "New",
        "last_name": "Subscriber",
        "status": "subscribed",
        "custom_fields": {"company": "New Corp"},
        "timezone": "UTC",
        "preferred_language": "en",
        "gdpr_consent": True,
        "is_active": True,
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "Test automation workflow",
        "status": "active",
        "trigger_type": "subscriber_added",
        "trigger_config": {"list_id": 1},
        "entry_conditions": [],
        "exit_conditions": [],
        "allow_re_entry": False,
        "max_entries_per_subscriber": 1,
    }


@pytest.fixture
def sample_analytics_data():
    """Sample analytics data for testing."""
    return {
        "date_from": "2024-01-01",
        "date_to": "2024-01-31",
        "campaign_id": None,
        "metrics": ["opens", "clicks", "bounces"],
    }


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "celery: mark test as requiring Celery")
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
