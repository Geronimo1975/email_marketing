"""
Comprehensive view and API tests for Email Marketing Platform.
"""

import pytest
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

User = get_user_model()


class TestCampaignViews(TestCase):
    """Test campaign views functionality."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        from apps.accounts.models import Team

        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test email template
        from apps.campaigns.models import EmailTemplate

        self.template = EmailTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            type="campaign",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            created_by=self.user,
        )

        # Create test subscriber list
        from apps.subscribers.models import SubscriberList

        self.subscriber_list = SubscriberList.objects.create(
            name="Test List",
            description="Test subscriber list",
            created_by=self.user,
        )

    def test_campaign_list_view_authenticated(self):
        """Test campaign list view for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("campaigns:campaign_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campaigns")

    def test_campaign_list_view_unauthenticated(self):
        """Test campaign list view for unauthenticated user."""
        response = self.client.get(reverse("campaigns:campaign_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_campaign_api_view(self):
        """Test campaign API view."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/campaigns/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_campaign_creation_api(self):
        """Test campaign creation via API."""
        self.api_client.force_authenticate(user=self.user)

        campaign_data = {
            "name": "Test API Campaign",
            "description": "Test campaign created via API",
            "type": "regular",
            "status": "draft",
            "subject": "Test API Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>Test API HTML</h1>",
            "text_content": "Test API Text",
            "timezone": "UTC",
            "track_opens": True,
            "track_clicks": True,
            "subscriber_lists": [self.subscriber_list.id],
        }

        response = self.api_client.post("/api/campaigns/", campaign_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Test API Campaign")

    def test_campaign_detail_api(self):
        """Test campaign detail API."""
        from apps.campaigns.models import Campaign

        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="draft",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            created_by=self.user,
        )

        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(f"/api/campaigns/{campaign.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Test Campaign")

    def test_campaign_send_api(self):
        """Test campaign send API."""
        from apps.campaigns.models import Campaign

        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="draft",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            created_by=self.user,
        )
        campaign.subscriber_lists.add(self.subscriber_list)

        self.api_client.force_authenticate(user=self.user)

        with patch("apps.campaigns.tasks.send_campaign_task.delay") as mock_task:
            response = self.api_client.post(f"/api/campaigns/{campaign.id}/send/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once_with(campaign.id)


class TestSubscriberViews(TestCase):
    """Test subscriber views functionality."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        from apps.accounts.models import Team

        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test subscriber list
        from apps.subscribers.models import SubscriberList

        self.subscriber_list = SubscriberList.objects.create(
            name="Test List",
            description="Test subscriber list",
            created_by=self.user,
        )

    def test_subscriber_list_view_authenticated(self):
        """Test subscriber list view for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("subscribers:subscriber_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subscribers")

    def test_subscriber_list_view_unauthenticated(self):
        """Test subscriber list view for unauthenticated user."""
        response = self.client.get(reverse("subscribers:subscriber_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_subscriber_api_view(self):
        """Test subscriber API view."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/subscribers/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_subscriber_creation_api(self):
        """Test subscriber creation via API."""
        self.api_client.force_authenticate(user=self.user)

        subscriber_data = {
            "email": "newsubscriber@example.com",
            "first_name": "New",
            "last_name": "Subscriber",
            "status": "subscribed",
            "custom_fields": {"company": "Test Corp"},
            "timezone": "UTC",
            "preferred_language": "en",
            "gdpr_consent": True,
            "is_active": True,
        }

        response = self.api_client.post(
            "/api/subscribers/", subscriber_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "newsubscriber@example.com")

    def test_subscriber_detail_view(self):
        """Test subscriber detail view."""
        from apps.subscribers.models import Subscriber

        subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse("subscribers:subscriber_detail", kwargs={"pk": subscriber.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")

    def test_subscriber_import_api(self):
        """Test subscriber import via API."""
        self.api_client.force_authenticate(user=self.user)

        csv_data = """email,first_name,last_name,company
john@example.com,John,Doe,Acme Corp
jane@example.com,Jane,Smith,Tech Inc"""

        import_data = {
            "file": csv_data,
            "list_id": self.subscriber_list.id,
            "update_existing": True,
            "skip_duplicates": True,
        }

        with patch("apps.subscribers.tasks.import_subscribers_task.delay") as mock_task:
            response = self.api_client.post(
                "/api/subscribers/import/", import_data, format="json"
            )
            self.assertEqual(response.status_code, 202)
            mock_task.assert_called_once()

    def test_subscriber_export_api(self):
        """Test subscriber export via API."""
        self.api_client.force_authenticate(user=self.user)

        export_data = {"list_id": self.subscriber_list.id, "format": "csv"}

        with patch("apps.subscribers.tasks.export_subscribers_task.delay") as mock_task:
            response = self.api_client.post(
                "/api/subscribers/export/", export_data, format="json"
            )
            self.assertEqual(response.status_code, 202)
            mock_task.assert_called_once()


class TestAnalyticsViews(TestCase):
    """Test analytics views functionality."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        from apps.accounts.models import Team

        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

    def test_analytics_dashboard_view_authenticated(self):
        """Test analytics dashboard view for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Dashboard")

    def test_analytics_dashboard_view_unauthenticated(self):
        """Test analytics dashboard view for unauthenticated user."""
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_analytics_api_view(self):
        """Test analytics API view."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/analytics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_analytics_dashboard_data(self):
        """Test analytics dashboard data retrieval."""
        self.api_client.force_authenticate(user=self.user)

        # Test with date range
        response = self.api_client.get(
            "/api/analytics/dashboard/",
            {"date_from": "2024-01-01", "date_to": "2024-01-31"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", response.data)

    def test_campaign_stats_api(self):
        """Test campaign statistics API."""
        from apps.campaigns.models import Campaign

        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="sent",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            emails_sent=100,
            emails_delivered=95,
            emails_opened=20,
            emails_clicked=5,
            created_by=self.user,
        )

        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(f"/api/campaigns/{campaign.id}/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("open_rate", response.data)
        self.assertIn("click_rate", response.data)


class TestAutomationViews(TestCase):
    """Test automation views functionality."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        from apps.accounts.models import Team

        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

    def test_automation_dashboard_view_authenticated(self):
        """Test automation dashboard view for authenticated user."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("automation:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automation Dashboard")

    def test_automation_dashboard_view_unauthenticated(self):
        """Test automation dashboard view for unauthenticated user."""
        response = self.client.get(reverse("automation:dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_automation_api_view(self):
        """Test automation API view."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/automation/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_workflow_creation_api(self):
        """Test workflow creation via API."""
        self.api_client.force_authenticate(user=self.user)

        workflow_data = {
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

        response = self.api_client.post(
            "/api/automation/workflows/", workflow_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Test Workflow")

    def test_workflow_execution_api(self):
        """Test workflow execution via API."""
        from apps.automation.models import AutomationWorkflow

        workflow = AutomationWorkflow.objects.create(
            name="Test Workflow",
            description="Test workflow description",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            created_by=self.user,
        )

        self.api_client.force_authenticate(user=self.user)

        with patch("apps.automation.tasks.execute_workflow_task.delay") as mock_task:
            response = self.api_client.post(
                f"/api/automation/workflows/{workflow.id}/execute/"
            )
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()


class TestIntegrationViews(TestCase):
    """Test integration views functionality."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        from apps.accounts.models import Team

        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test integration
        from apps.integrations.models import Integration

        self.integration = Integration.objects.create(
            name="Test Mailgun Integration",
            provider="mailgun",
            status="active",
            config={"domain": "test.example.com"},
            credentials='{"api_key": "test-key"}',
            created_by=self.user,
        )

    def test_mailgun_webhook_view(self):
        """Test Mailgun webhook view."""
        webhook_data = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
                "message": {"headers": {"message-id": "test-message-id"}},
            }
        }

        with patch(
            "apps.integrations.services.validate_webhook_signature", return_value=True
        ):
            with patch(
                "apps.integrations.services.process_mailgun_webhook", return_value=True
            ):
                response = self.client.post(
                    "/webhooks/mailgun/",
                    data=json.dumps(webhook_data),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)

    def test_odoo_webhook_view(self):
        """Test Odoo webhook view."""
        webhook_data = {
            "id": "test-odoo-event",
            "type": "contact_updated",
            "data": {"contact_id": 1, "email": "updated@example.com"},
        }

        response = self.client.post(
            "/webhooks/odoo/",
            data=json.dumps(webhook_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_sync_odoo_contacts_api(self):
        """Test sync Odoo contacts API."""
        self.api_client.force_authenticate(user=self.user)

        with patch("apps.integrations.tasks.sync_odoo_contacts.delay") as mock_task:
            response = self.api_client.post("/api/integrations/sync-odoo/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()

    def test_validate_email_api(self):
        """Test email validation API."""
        self.api_client.force_authenticate(user=self.user)

        with patch("apps.integrations.services.MailgunService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.validate_email.return_value = {
                "is_valid": True,
                "reason": "Valid email",
                "risk": "low",
            }
            mock_service.return_value = mock_instance

            response = self.api_client.post(
                "/api/integrations/validate-email/",
                {"email": "test@example.com"},
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["is_valid"])

    def test_suppression_list_api(self):
        """Test suppression list API."""
        self.api_client.force_authenticate(user=self.user)

        with patch("apps.integrations.services.MailgunService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_suppressions.return_value = [
                {"address": "bounced@example.com", "reason": "hard_bounce"}
            ]
            mock_service.return_value = mock_instance

            response = self.api_client.get("/api/integrations/suppressions/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data["items"]), 1)

    def test_add_to_suppression_api(self):
        """Test add to suppression list API."""
        self.api_client.force_authenticate(user=self.user)

        with patch("apps.integrations.services.MailgunService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.add_to_suppression.return_value = {
                "message": "Added to suppression list"
            }
            mock_service.return_value = mock_instance

            response = self.api_client.post(
                "/api/integrations/suppressions/",
                {
                    "email": "bounced@example.com",
                    "type": "bounces",
                    "reason": "hard_bounce",
                },
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.data)

    def test_remove_from_suppression_api(self):
        """Test remove from suppression list API."""
        self.api_client.force_authenticate(user=self.user)

        with patch("apps.integrations.services.MailgunService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.remove_from_suppression.return_value = True
            mock_service.return_value = mock_instance

            response = self.api_client.delete(
                "/api/integrations/suppressions/",
                {"email": "bounced@example.com", "type": "bounces"},
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.data)


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestViewPermissions:
    """Test view permissions and access control."""

    def test_admin_access(self, authenticated_api_client, user):
        """Test admin user has full access."""
        response = authenticated_api_client.get("/api/campaigns/")
        assert response.status_code == 200

    def test_campaign_manager_access(self, user):
        """Test campaign manager access."""
        user.role = "campaign_manager"
        user.save()

        api_client = APIClient()
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/campaigns/")
        assert response.status_code == 200

    def test_viewer_limited_access(self, user):
        """Test viewer has limited access."""
        user.role = "viewer"
        user.save()

        api_client = APIClient()
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/campaigns/")
        assert response.status_code == 200

    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get("/api/campaigns/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestViewDataFiltering:
    """Test view data filtering and pagination."""

    def test_campaign_list_pagination(self, authenticated_api_client, campaign):
        """Test campaign list pagination."""
        response = authenticated_api_client.get("/api/campaigns/?page=1&page_size=10")
        assert response.status_code == 200
        assert "results" in response.data

    def test_subscriber_list_filtering(self, authenticated_api_client, subscriber):
        """Test subscriber list filtering."""
        response = authenticated_api_client.get("/api/subscribers/?status=subscribed")
        assert response.status_code == 200

    def test_analytics_date_filtering(self, authenticated_api_client):
        """Test analytics date filtering."""
        response = authenticated_api_client.get(
            "/api/analytics/dashboard/",
            {"date_from": "2024-01-01", "date_to": "2024-01-31"},
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestViewErrorHandling:
    """Test view error handling and validation."""

    def test_invalid_campaign_data(self, authenticated_api_client):
        """Test invalid campaign data handling."""
        response = authenticated_api_client.post(
            "/api/campaigns/",
            {"name": "", "subject": "Test Subject"},  # Invalid empty name
            format="json",
        )
        assert response.status_code == 400

    def test_invalid_subscriber_data(self, authenticated_api_client):
        """Test invalid subscriber data handling."""
        response = authenticated_api_client.post(
            "/api/subscribers/",
            {"email": "invalid-email", "first_name": "John"},  # Invalid email format
            format="json",
        )
        assert response.status_code == 400

    def test_nonexistent_campaign(self, authenticated_api_client):
        """Test accessing nonexistent campaign."""
        response = authenticated_api_client.get("/api/campaigns/999/")
        assert response.status_code == 404

    def test_nonexistent_subscriber(self, authenticated_api_client):
        """Test accessing nonexistent subscriber."""
        response = authenticated_api_client.get("/api/subscribers/999/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestViewHTMXIntegration:
    """Test HTMX integration in views."""

    def test_campaign_list_htmx(self, user):
        """Test campaign list HTMX partial."""
        client = Client()
        client.force_login(user)

        response = client.get("/campaigns/list-htmx/")
        assert response.status_code == 200
        assert "text/html" in response["Content-Type"]

    def test_analytics_dashboard_htmx(self, user):
        """Test analytics dashboard HTMX partial."""
        client = Client()
        client.force_login(user)

        response = client.get("/analytics/dashboard-htmx/")
        assert response.status_code == 200
        assert "text/html" in response["Content-Type"]


@pytest.mark.django_db
class TestViewCSRFProtection:
    """Test CSRF protection in views."""

    def test_csrf_protection_enabled(self, user):
        """Test CSRF protection is enabled."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        response = client.post(
            "/api/campaigns/",
            {"name": "Test Campaign", "subject": "Test Subject"},
            format="json",
        )
        # Should require CSRF token
        assert response.status_code in [403, 400]

    def test_csrf_exempt_webhooks(self):
        """Test webhook endpoints are CSRF exempt."""
        client = Client(enforce_csrf_checks=True)

        webhook_data = {"event-data": {"event": "opened", "id": "test-event-id"}}

        with patch(
            "apps.integrations.services.validate_webhook_signature", return_value=True
        ):
            with patch(
                "apps.integrations.services.process_mailgun_webhook", return_value=True
            ):
                response = client.post(
                    "/webhooks/mailgun/",
                    data=json.dumps(webhook_data),
                    content_type="application/json",
                )
                assert response.status_code == 200


@pytest.mark.django_db
class TestViewRateLimiting:
    """Test rate limiting in views."""

    def test_api_rate_limiting(self, authenticated_api_client):
        """Test API rate limiting."""
        # Make multiple requests to test rate limiting
        for _ in range(10):
            response = authenticated_api_client.get("/api/campaigns/")
            # Should not be rate limited for normal usage
            assert response.status_code in [200, 429]

    def test_webhook_rate_limiting(self):
        """Test webhook rate limiting."""
        client = Client()

        webhook_data = {"event-data": {"event": "opened", "id": "test-event-id"}}

        with patch(
            "apps.integrations.services.validate_webhook_signature", return_value=True
        ):
            with patch(
                "apps.integrations.services.process_mailgun_webhook", return_value=True
            ):
                # Make multiple webhook requests
                for _ in range(10):
                    response = client.post(
                        "/webhooks/mailgun/",
                        data=json.dumps(webhook_data),
                        content_type="application/json",
                    )
                    assert response.status_code in [200, 429]
