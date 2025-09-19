"""
End-to-end integration tests for Email Marketing Platform.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APIClient
from rest_framework import status
import requests
from requests.exceptions import RequestException

from apps.accounts.models import User, Team
from apps.campaigns.models import Campaign, EmailTemplate
from apps.subscribers.models import Subscriber, SubscriberList
from apps.analytics.models import EmailEvent
from apps.automation.models import AutomationWorkflow, WorkflowStep
from apps.integrations.models import Integration, WebhookEndpoint


class TestCampaignWorkflow(TransactionTestCase):
    """Test complete campaign workflow from creation to analytics."""

    def setUp(self):
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test email template
        self.template = EmailTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            type="campaign",
            subject="Test Subject",
            html_content="<h1>Hello {{first_name}}</h1>",
            text_content="Hello {{first_name}}",
            created_by=self.user,
        )

        # Create test subscriber list
        self.subscriber_list = SubscriberList.objects.create(
            name="Test List",
            description="Test subscriber list",
            created_by=self.user,
        )

        # Create test subscribers
        self.subscriber1 = Subscriber.objects.create(
            email="subscriber1@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )
        self.subscriber2 = Subscriber.objects.create(
            email="subscriber2@example.com",
            first_name="Jane",
            last_name="Smith",
            status="subscribed",
        )
        self.subscriber_list.subscribers.add(self.subscriber1, self.subscriber2)

    def test_complete_campaign_workflow(self):
        """Test complete campaign workflow from creation to sending."""
        self.client.force_authenticate(user=self.user)

        # 1. Create campaign
        campaign_data = {
            "name": "Integration Test Campaign",
            "description": "Test campaign for integration testing",
            "type": "regular",
            "status": "draft",
            "subject": "Test Campaign Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>Test Campaign HTML</h1>",
            "text_content": "Test Campaign Text",
            "timezone": "UTC",
            "track_opens": True,
            "track_clicks": True,
            "subscriber_lists": [self.subscriber_list.id],
        }

        response = self.client.post("/api/campaigns/", campaign_data, format="json")
        self.assertEqual(response.status_code, 201)
        campaign_id = response.data["id"]

        # 2. Update campaign with template
        update_data = {
            "template": self.template.id,
            "html_content": "<h1>Hello {{first_name}}</h1>",
            "text_content": "Hello {{first_name}}",
        }

        response = self.client.patch(
            f"/api/campaigns/{campaign_id}/", update_data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        # 3. Send campaign
        with patch("apps.campaigns.tasks.send_campaign_task.delay") as mock_task:
            response = self.client.post(f"/api/campaigns/{campaign_id}/send/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once_with(campaign_id)

        # 4. Verify campaign status
        response = self.client.get(f"/api/campaigns/{campaign_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "sending")

    def test_campaign_analytics_workflow(self):
        """Test campaign analytics workflow."""
        # Create and send campaign
        campaign = Campaign.objects.create(
            name="Analytics Test Campaign",
            description="Test campaign for analytics",
            type="regular",
            status="sent",
            subject="Analytics Test Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Analytics Test HTML</h1>",
            text_content="Analytics Test Text",
            emails_sent=100,
            emails_delivered=95,
            emails_opened=20,
            emails_clicked=5,
            created_by=self.user,
        )

        # Create email events
        EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-1",
            mailgun_event_id="test-event-1",
            recipient_email="subscriber1@example.com",
            subscriber=self.subscriber1,
            campaign=campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
        )

        EmailEvent.objects.create(
            event_type="clicked",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-2",
            mailgun_event_id="test-event-2",
            recipient_email="subscriber2@example.com",
            subscriber=self.subscriber2,
            campaign=campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.2",
            device_type="mobile",
            country="CA",
        )

        self.client.force_authenticate(user=self.user)

        # Get campaign analytics
        response = self.client.get(f"/api/campaigns/{campaign.id}/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("open_rate", response.data)
        self.assertIn("click_rate", response.data)
        self.assertIn("events", response.data)

    def test_campaign_ab_testing_workflow(self):
        """Test campaign A/B testing workflow."""
        self.client.force_authenticate(user=self.user)

        # Create A/B test campaign
        campaign_data = {
            "name": "AB Test Campaign",
            "description": "A/B test campaign",
            "type": "ab_test",
            "status": "draft",
            "subject": "AB Test Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>AB Test HTML</h1>",
            "text_content": "AB Test Text",
            "timezone": "UTC",
            "track_opens": True,
            "track_clicks": True,
            "subscriber_lists": [self.subscriber_list.id],
        }

        response = self.client.post("/api/campaigns/", campaign_data, format="json")
        self.assertEqual(response.status_code, 201)
        campaign_id = response.data["id"]

        # Create A/B test variants
        variant_a_data = {
            "name": "Variant A",
            "subject": "Subject A",
            "html_content": "<h1>Variant A HTML</h1>",
            "text_content": "Variant A Text",
            "split_percentage": 50,
        }

        variant_b_data = {
            "name": "Variant B",
            "subject": "Subject B",
            "html_content": "<h1>Variant B HTML</h1>",
            "text_content": "Variant B Text",
            "split_percentage": 50,
        }

        response = self.client.post(
            f"/api/campaigns/{campaign_id}/variants/", variant_a_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/campaigns/{campaign_id}/variants/", variant_b_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        # Send A/B test
        with patch("apps.campaigns.tasks.send_campaign_task.delay") as mock_task:
            response = self.client.post(f"/api/campaigns/{campaign_id}/send/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once_with(campaign_id)


class TestSubscriberWorkflow(TransactionTestCase):
    """Test complete subscriber workflow from import to segmentation."""

    def setUp(self):
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test subscriber list
        self.subscriber_list = SubscriberList.objects.create(
            name="Test List",
            description="Test subscriber list",
            created_by=self.user,
        )

    def test_complete_subscriber_workflow(self):
        """Test complete subscriber workflow from import to segmentation."""
        self.client.force_authenticate(user=self.user)

        # 1. Import subscribers
        csv_data = """email,first_name,last_name,company,industry
john@example.com,John,Doe,Acme Corp,Technology
jane@example.com,Jane,Smith,Tech Inc,Software
bob@example.com,Bob,Johnson,Data Co,Analytics"""

        import_data = {
            "file": csv_data,
            "list_id": self.subscriber_list.id,
            "update_existing": True,
            "skip_duplicates": True,
        }

        with patch("apps.subscribers.tasks.import_subscribers_task.delay") as mock_task:
            response = self.client.post(
                "/api/subscribers/import/", import_data, format="json"
            )
            self.assertEqual(response.status_code, 202)
            mock_task.assert_called_once()

        # 2. Create subscribers manually
        subscriber_data = {
            "email": "manual@example.com",
            "first_name": "Manual",
            "last_name": "User",
            "status": "subscribed",
            "custom_fields": {"company": "Manual Corp"},
            "timezone": "UTC",
            "preferred_language": "en",
            "gdpr_consent": True,
            "is_active": True,
        }

        response = self.client.post("/api/subscribers/", subscriber_data, format="json")
        self.assertEqual(response.status_code, 201)

        # 3. Create segments
        segment_data = {
            "name": "High Engagement",
            "description": "High engagement subscribers",
            "rules": [{"field": "engagement_score", "operator": "gte", "value": 0.7}],
        }

        response = self.client.post(
            "/api/subscribers/segments/", segment_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        # 4. Export subscribers
        export_data = {
            "list_id": self.subscriber_list.id,
            "format": "csv",
            "fields": ["email", "first_name", "last_name", "company"],
        }

        with patch("apps.subscribers.tasks.export_subscribers_task.delay") as mock_task:
            response = self.client.post(
                "/api/subscribers/export/", export_data, format="json"
            )
            self.assertEqual(response.status_code, 202)
            mock_task.assert_called_once()

    def test_subscriber_engagement_workflow(self):
        """Test subscriber engagement tracking workflow."""
        # Create subscriber
        subscriber = Subscriber.objects.create(
            email="engagement@example.com",
            first_name="Engagement",
            last_name="User",
            status="subscribed",
        )

        # Create campaign
        campaign = Campaign.objects.create(
            name="Engagement Test Campaign",
            description="Test campaign for engagement tracking",
            type="regular",
            status="sent",
            subject="Engagement Test Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Engagement Test HTML</h1>",
            text_content="Engagement Test Text",
            created_by=self.user,
        )

        # Create email events
        EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-1",
            mailgun_event_id="test-event-1",
            recipient_email=subscriber.email,
            subscriber=subscriber,
            campaign=campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
        )

        EmailEvent.objects.create(
            event_type="clicked",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-2",
            mailgun_event_id="test-event-2",
            recipient_email=subscriber.email,
            subscriber=subscriber,
            campaign=campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
        )

        self.client.force_authenticate(user=self.user)

        # Update engagement
        with patch(
            "apps.subscribers.tasks.update_subscriber_engagement_task.delay"
        ) as mock_task:
            response = self.client.post(
                f"/api/subscribers/{subscriber.id}/update-engagement/"
            )
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once_with(subscriber.id)


class TestAutomationWorkflow(TransactionTestCase):
    """Test complete automation workflow from creation to execution."""

    def setUp(self):
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test email template
        self.template = EmailTemplate.objects.create(
            name="Automation Template",
            description="Template for automation",
            type="automation",
            subject="Automation Subject",
            html_content="<h1>Automation HTML</h1>",
            text_content="Automation Text",
            created_by=self.user,
        )

        # Create test subscriber
        self.subscriber = Subscriber.objects.create(
            email="automation@example.com",
            first_name="Automation",
            last_name="User",
            status="subscribed",
        )

    def test_complete_automation_workflow(self):
        """Test complete automation workflow from creation to execution."""
        self.client.force_authenticate(user=self.user)

        # 1. Create workflow
        workflow_data = {
            "name": "Integration Test Workflow",
            "description": "Test workflow for integration testing",
            "status": "active",
            "trigger_type": "subscriber_added",
            "trigger_config": {"list_id": 1},
            "entry_conditions": [
                {"field": "status", "operator": "equals", "value": "subscribed"}
            ],
            "exit_conditions": [],
            "allow_re_entry": False,
            "max_entries_per_subscriber": 1,
        }

        response = self.client.post(
            "/api/automation/workflows/", workflow_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        workflow_id = response.data["id"]

        # 2. Create workflow step
        step_data = {
            "name": "Welcome Email",
            "step_type": "email",
            "order": 1,
            "config": {
                "template_id": self.template.id,
                "subject": "Welcome to our service!",
            },
            "is_active": True,
        }

        response = self.client.post(
            f"/api/automation/workflows/{workflow_id}/steps/", step_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        # 3. Execute workflow
        with patch("apps.automation.tasks.execute_workflow_task.delay") as mock_task:
            response = self.client.post(
                f"/api/automation/workflows/{workflow_id}/execute/"
            )
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()

        # 4. Get workflow metrics
        response = self.client.get(f"/api/automation/workflows/{workflow_id}/metrics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_entries", response.data)
        self.assertIn("completed_workflows", response.data)

    def test_automation_trigger_workflow(self):
        """Test automation trigger workflow."""
        # Create workflow
        workflow = AutomationWorkflow.objects.create(
            name="Trigger Test Workflow",
            description="Test workflow for trigger testing",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            created_by=self.user,
        )

        # Create workflow step
        WorkflowStep.objects.create(
            workflow=workflow,
            name="Welcome Step",
            step_type="email",
            order=1,
            config={"template_id": self.template.id, "subject": "Welcome!"},
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        # Trigger workflow
        trigger_data = {
            "subscriber_id": self.subscriber.id,
            "trigger_data": {"list_id": 1},
        }

        with patch("apps.automation.tasks.execute_workflow_task.delay") as mock_task:
            response = self.client.post(
                f"/api/automation/workflows/{workflow.id}/trigger/",
                trigger_data,
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()


class TestIntegrationWorkflow(TransactionTestCase):
    """Test complete integration workflow from setup to webhook processing."""

    def setUp(self):
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

    def test_mailgun_integration_workflow(self):
        """Test complete Mailgun integration workflow."""
        self.client.force_authenticate(user=self.user)

        # 1. Create Mailgun integration
        integration_data = {
            "name": "Test Mailgun Integration",
            "provider": "mailgun",
            "status": "active",
            "config": {"domain": "test.example.com"},
            "credentials": {"api_key": "test-api-key"},
            "is_active": True,
        }

        response = self.client.post(
            "/api/integrations/", integration_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        integration_id = response.data["id"]

        # 2. Create webhook endpoint
        webhook_data = {
            "name": "Test Mailgun Webhook",
            "event_type": "mailgun_delivery",
            "url_path": "test-mailgun-webhook",
            "integration": integration_id,
            "secret_key": "test-secret-key",
            "verify_signature": True,
            "is_active": True,
            "max_retries": 3,
            "retry_delay": 60,
        }

        response = self.client.post(
            "/api/integrations/webhooks/", webhook_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        # 3. Test webhook processing
        webhook_payload = {
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

        with patch(
            "apps.integrations.services.validate_webhook_signature", return_value=True
        ):
            with patch(
                "apps.integrations.services.process_mailgun_webhook", return_value=True
            ):
                response = self.client.post(
                    "/webhooks/mailgun/",
                    data=json.dumps(webhook_payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)

    def test_odoo_integration_workflow(self):
        """Test complete Odoo integration workflow."""
        self.client.force_authenticate(user=self.user)

        # 1. Create Odoo integration
        integration_data = {
            "name": "Test Odoo Integration",
            "provider": "odoo",
            "status": "active",
            "config": {"url": "https://test.odoo.com", "database": "test_db"},
            "credentials": {"username": "testuser", "api_key": "test-api-key"},
            "is_active": True,
        }

        response = self.client.post(
            "/api/integrations/", integration_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        integration_id = response.data["id"]

        # 2. Test Odoo sync
        with patch("apps.integrations.tasks.sync_odoo_contacts.delay") as mock_task:
            response = self.client.post("/api/integrations/sync-odoo/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()

        # 3. Test Odoo webhook
        webhook_data = {
            "id": "test-odoo-event",
            "type": "contact_updated",
            "data": {
                "contact_id": 1,
                "email": "updated@example.com",
                "name": "Updated Contact",
            },
        }

        response = self.client.post(
            "/webhooks/odoo/",
            data=json.dumps(webhook_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_email_validation_workflow(self):
        """Test email validation workflow."""
        self.client.force_authenticate(user=self.user)

        # Test email validation
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.validate_email.return_value = {
                "is_valid": True,
                "reason": "Valid email",
                "risk": "low",
            }
            mock_service_class.return_value = mock_service

            response = self.client.post(
                "/api/integrations/validate-email/",
                {"email": "test@example.com"},
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["is_valid"])

    def test_suppression_list_workflow(self):
        """Test suppression list management workflow."""
        self.client.force_authenticate(user=self.user)

        # Test get suppressions
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_suppressions.return_value = [
                {"address": "bounced@example.com", "reason": "hard_bounce"}
            ]
            mock_service_class.return_value = mock_service

            response = self.client.get("/api/integrations/suppressions/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data["items"]), 1)

        # Test add to suppression
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.add_to_suppression.return_value = {
                "message": "Added to suppression list"
            }
            mock_service_class.return_value = mock_service

            response = self.client.post(
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

        # Test remove from suppression
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.remove_from_suppression.return_value = True
            mock_service_class.return_value = mock_service

            response = self.client.delete(
                "/api/integrations/suppressions/",
                {"email": "bounced@example.com", "type": "bounces"},
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.data)


class TestAnalyticsWorkflow(TransactionTestCase):
    """Test complete analytics workflow from data collection to reporting."""

    def setUp(self):
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            role="admin",
        )

        # Create test team
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.user
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Analytics Test Campaign",
            description="Test campaign for analytics",
            type="regular",
            status="sent",
            subject="Analytics Test Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Analytics Test HTML</h1>",
            text_content="Analytics Test Text",
            emails_sent=100,
            emails_delivered=95,
            emails_opened=20,
            emails_clicked=5,
            created_by=self.user,
        )

        # Create test subscriber
        self.subscriber = Subscriber.objects.create(
            email="analytics@example.com",
            first_name="Analytics",
            last_name="User",
            status="subscribed",
        )

    def test_complete_analytics_workflow(self):
        """Test complete analytics workflow from data collection to reporting."""
        self.client.force_authenticate(user=self.user)

        # 1. Create email events
        EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-1",
            mailgun_event_id="test-event-1",
            recipient_email=self.subscriber.email,
            subscriber=self.subscriber,
            campaign=self.campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
            region="CA",
            city="San Francisco",
        )

        EmailEvent.objects.create(
            event_type="clicked",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-2",
            mailgun_event_id="test-event-2",
            recipient_email=self.subscriber.email,
            subscriber=self.subscriber,
            campaign=self.campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
            region="CA",
            city="San Francisco",
        )

        # 2. Get dashboard data
        response = self.client.get(
            "/api/analytics/dashboard/",
            {"date_from": "2024-01-01", "date_to": "2024-01-31"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("stats", response.data)
        self.assertIn("charts", response.data)

        # 3. Get campaign analytics
        response = self.client.get(f"/api/campaigns/{self.campaign.id}/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("open_rate", response.data)
        self.assertIn("click_rate", response.data)
        self.assertIn("events", response.data)

        # 4. Generate campaign report
        with patch(
            "apps.analytics.tasks.generate_campaign_report_task.delay"
        ) as mock_task:
            response = self.client.post(
                f"/api/campaigns/{self.campaign.id}/generate-report/",
                {"date_from": "2024-01-01", "date_to": "2024-01-31"},
                format="json",
            )
            self.assertEqual(response.status_code, 202)
            mock_task.assert_called_once()

    def test_analytics_data_processing_workflow(self):
        """Test analytics data processing workflow."""
        # Create multiple email events
        for i in range(10):
            EmailEvent.objects.create(
                event_type="opened",
                timestamp=timezone.now() - timedelta(hours=i),
                mailgun_message_id=f"test-message-{i}",
                mailgun_event_id=f"test-event-{i}",
                recipient_email=f"user{i}@example.com",
                subscriber=self.subscriber,
                campaign=self.campaign,
                user_agent="Mozilla/5.0 (Test Browser)",
                ip_address=f"192.168.1.{i}",
                device_type="desktop",
                country="US",
            )

        self.client.force_authenticate(user=self.user)

        # Process analytics data
        with patch("apps.analytics.tasks.update_analytics_task.delay") as mock_task:
            response = self.client.post("/api/analytics/process/")
            self.assertEqual(response.status_code, 200)
            mock_task.assert_called_once()

        # Get analytics metrics
        response = self.client.get("/api/analytics/metrics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_opens", response.data)
        self.assertIn("total_clicks", response.data)
        self.assertIn("total_bounces", response.data)


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestEndToEndWorkflows:
    """Test end-to-end workflows with pytest."""

    def test_complete_email_marketing_workflow(
        self, user, team, subscriber_list, subscriber
    ):
        """Test complete email marketing workflow from start to finish."""
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Create campaign
        campaign_data = {
            "name": "E2E Test Campaign",
            "description": "End-to-end test campaign",
            "type": "regular",
            "status": "draft",
            "subject": "E2E Test Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>E2E Test HTML</h1>",
            "text_content": "E2E Test Text",
            "timezone": "UTC",
            "track_opens": True,
            "track_clicks": True,
            "subscriber_lists": [subscriber_list.id],
        }

        response = client.post("/api/campaigns/", campaign_data, format="json")
        assert response.status_code == 201
        campaign_id = response.data["id"]

        # 2. Send campaign
        with patch("apps.campaigns.tasks.send_campaign_task.delay") as mock_task:
            response = client.post(f"/api/campaigns/{campaign_id}/send/")
            assert response.status_code == 200
            mock_task.assert_called_once_with(campaign_id)

        # 3. Create email event
        from apps.analytics.models import EmailEvent
        from apps.campaigns.models import Campaign

        campaign = Campaign.objects.get(id=campaign_id)
        EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-id",
            mailgun_event_id="test-event-id",
            recipient_email=subscriber.email,
            subscriber=subscriber,
            campaign=campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
        )

        # 4. Get analytics
        response = client.get(f"/api/campaigns/{campaign_id}/stats/")
        assert response.status_code == 200
        assert "open_rate" in response.data

    def test_complete_automation_workflow(self, user, team, subscriber):
        """Test complete automation workflow from start to finish."""
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Create workflow
        workflow_data = {
            "name": "E2E Test Workflow",
            "description": "End-to-end test workflow",
            "status": "active",
            "trigger_type": "subscriber_added",
            "trigger_config": {"list_id": 1},
            "entry_conditions": [],
            "exit_conditions": [],
            "allow_re_entry": False,
            "max_entries_per_subscriber": 1,
        }

        response = client.post(
            "/api/automation/workflows/", workflow_data, format="json"
        )
        assert response.status_code == 201
        workflow_id = response.data["id"]

        # 2. Create workflow step
        step_data = {
            "name": "Welcome Step",
            "step_type": "email",
            "order": 1,
            "config": {"subject": "Welcome!"},
            "is_active": True,
        }

        response = client.post(
            f"/api/automation/workflows/{workflow_id}/steps/", step_data, format="json"
        )
        assert response.status_code == 201

        # 3. Execute workflow
        with patch("apps.automation.tasks.execute_workflow_task.delay") as mock_task:
            response = client.post(f"/api/automation/workflows/{workflow_id}/execute/")
            assert response.status_code == 200
            mock_task.assert_called_once()

    def test_complete_integration_workflow(self, user, team):
        """Test complete integration workflow from start to finish."""
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Create integration
        integration_data = {
            "name": "E2E Test Integration",
            "provider": "mailgun",
            "status": "active",
            "config": {"domain": "test.example.com"},
            "credentials": {"api_key": "test-key"},
            "is_active": True,
        }

        response = client.post("/api/integrations/", integration_data, format="json")
        assert response.status_code == 201
        integration_id = response.data["id"]

        # 2. Create webhook endpoint
        webhook_data = {
            "name": "E2E Test Webhook",
            "event_type": "mailgun_delivery",
            "url_path": "test-webhook",
            "integration": integration_id,
            "secret_key": "test-secret",
            "verify_signature": True,
            "is_active": True,
        }

        response = client.post(
            "/api/integrations/webhooks/", webhook_data, format="json"
        )
        assert response.status_code == 201

        # 3. Test webhook
        webhook_payload = {
            "event-data": {
                "event": "opened",
                "id": "test-event-id",
                "timestamp": 1640995200,
                "recipient": "test@example.com",
            }
        }

        with patch(
            "apps.integrations.services.validate_webhook_signature", return_value=True
        ):
            with patch(
                "apps.integrations.services.process_mailgun_webhook", return_value=True
            ):
                response = client.post(
                    "/webhooks/mailgun/",
                    data=json.dumps(webhook_payload),
                    content_type="application/json",
                )
                assert response.status_code == 200


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling in end-to-end workflows."""

    def test_campaign_workflow_error_handling(self, user, team):
        """Test error handling in campaign workflow."""
        client = APIClient()
        client.force_authenticate(user=user)

        # Test invalid campaign data
        invalid_data = {
            "name": "",  # Empty name
            "subject": "",  # Empty subject
            "from_email": "invalid-email",  # Invalid email
        }

        response = client.post("/api/campaigns/", invalid_data, format="json")
        assert response.status_code == 400

        # Test non-existent campaign
        response = client.get("/api/campaigns/999/")
        assert response.status_code == 404

    def test_subscriber_workflow_error_handling(self, user, team):
        """Test error handling in subscriber workflow."""
        client = APIClient()
        client.force_authenticate(user=user)

        # Test invalid subscriber data
        invalid_data = {
            "email": "invalid-email",  # Invalid email
            "first_name": "",  # Empty name
            "status": "invalid-status",  # Invalid status
        }

        response = client.post("/api/subscribers/", invalid_data, format="json")
        assert response.status_code == 400

        # Test non-existent subscriber
        response = client.get("/api/subscribers/999/")
        assert response.status_code == 404

    def test_automation_workflow_error_handling(self, user, team):
        """Test error handling in automation workflow."""
        client = APIClient()
        client.force_authenticate(user=user)

        # Test invalid workflow data
        invalid_data = {
            "name": "",  # Empty name
            "trigger_type": "invalid-trigger",  # Invalid trigger
            "status": "invalid-status",  # Invalid status
        }

        response = client.post(
            "/api/automation/workflows/", invalid_data, format="json"
        )
        assert response.status_code == 400

        # Test non-existent workflow
        response = client.get("/api/automation/workflows/999/")
        assert response.status_code == 404

    def test_integration_workflow_error_handling(self, user, team):
        """Test error handling in integration workflow."""
        client = APIClient()
        client.force_authenticate(user=user)

        # Test invalid integration data
        invalid_data = {
            "name": "",  # Empty name
            "provider": "invalid-provider",  # Invalid provider
            "status": "invalid-status",  # Invalid status
        }

        response = client.post("/api/integrations/", invalid_data, format="json")
        assert response.status_code == 400

        # Test non-existent integration
        response = client.get("/api/integrations/999/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestPerformance:
    """Test performance in end-to-end workflows."""

    def test_campaign_performance(self, user, team, subscriber_list):
        """Test campaign performance with large datasets."""
        # Create multiple subscribers
        from apps.subscribers.models import Subscriber

        subscribers = []
        for i in range(100):
            subscriber = Subscriber.objects.create(
                email=f"user{i}@example.com",
                first_name=f"User{i}",
                last_name="Test",
                status="subscribed",
                team=team,
            )
            subscribers.append(subscriber)
            subscriber_list.subscribers.add(subscriber)

        client = APIClient()
        client.force_authenticate(user=user)

        # Create campaign
        campaign_data = {
            "name": "Performance Test Campaign",
            "description": "Performance test campaign",
            "type": "regular",
            "status": "draft",
            "subject": "Performance Test Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>Performance Test HTML</h1>",
            "text_content": "Performance Test Text",
            "timezone": "UTC",
            "track_opens": True,
            "track_clicks": True,
            "subscriber_lists": [subscriber_list.id],
        }

        response = client.post("/api/campaigns/", campaign_data, format="json")
        assert response.status_code == 201

        # Send campaign
        with patch("apps.campaigns.tasks.send_campaign_task.delay") as mock_task:
            response = client.post(f'/api/campaigns/{response.data["id"]}/send/')
            assert response.status_code == 200
            mock_task.assert_called_once()

    def test_analytics_performance(self, user, team, campaign, subscriber):
        """Test analytics performance with large datasets."""
        # Create multiple email events
        from apps.analytics.models import EmailEvent

        for i in range(100):
            EmailEvent.objects.create(
                event_type="opened",
                timestamp=timezone.now() - timedelta(hours=i),
                mailgun_message_id=f"test-message-{i}",
                mailgun_event_id=f"test-event-{i}",
                recipient_email=f"user{i}@example.com",
                subscriber=subscriber,
                campaign=campaign,
                user_agent="Mozilla/5.0 (Test Browser)",
                ip_address=f"192.168.1.{i % 255}",
                device_type="desktop",
                country="US",
            )

        client = APIClient()
        client.force_authenticate(user=user)

        # Get analytics
        response = client.get("/api/analytics/dashboard/")
        assert response.status_code == 200
        assert "stats" in response.data
