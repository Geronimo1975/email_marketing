"""
Comprehensive model tests for Email Marketing Platform.
"""

import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from apps.accounts.models import User, Team, TeamMembership, APIKey
from apps.campaigns.models import (
    Campaign,
    EmailTemplate,
    CampaignRecipient,
    CampaignVariant,
)
from apps.subscribers.models import (
    Subscriber,
    SubscriberList,
    Tag,
    SegmentRule,
    Subscription,
)
from apps.analytics.models import (
    EmailEvent,
    CampaignReport,
    SubscriberActivity,
    LinkClick,
    DomainReputation,
)
from apps.integrations.models import Integration, WebhookEndpoint, WebhookLog, SyncJob
from apps.automation.models import AutomationWorkflow, WorkflowStep, WorkflowSubscriber


class TestUserModel(TestCase):
    """Test User model functionality."""

    def test_user_creation(self):
        """Test user creation with required fields."""
        user = User.objects.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))

    def test_user_email_unique(self):
        """Test that email must be unique."""
        User.objects.create_user(
            email="test@example.com", username="testuser1", password="testpass123"
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com", username="testuser2", password="testpass123"
            )

    def test_user_role_properties(self):
        """Test user role properties."""
        admin_user = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="testpass123",
            role="admin",
        )
        campaign_manager = User.objects.create_user(
            email="manager@example.com",
            username="manager",
            password="testpass123",
            role="campaign_manager",
        )
        viewer = User.objects.create_user(
            email="viewer@example.com",
            username="viewer",
            password="testpass123",
            role="viewer",
        )

        self.assertTrue(admin_user.is_admin)
        self.assertTrue(admin_user.is_campaign_manager)
        self.assertTrue(campaign_manager.is_campaign_manager)
        self.assertFalse(campaign_manager.is_admin)
        self.assertFalse(viewer.is_campaign_manager)
        self.assertFalse(viewer.is_admin)

    def test_user_str_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )
        self.assertEqual(str(user), "test@example.com")


class TestTeamModel(TestCase):
    """Test Team model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )

    def test_team_creation(self):
        """Test team creation."""
        team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.assertEqual(team.name, "Test Team")
        self.assertEqual(team.owner, self.owner)

    def test_team_str_representation(self):
        """Test team string representation."""
        team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.assertEqual(str(team), "Test Team")


class TestEmailTemplateModel(TestCase):
    """Test EmailTemplate model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )

    def test_email_template_creation(self):
        """Test email template creation."""
        template = EmailTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            type="campaign",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            variables=["first_name", "last_name"],
            created_by=self.owner,
        )
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.type, "campaign")
        self.assertEqual(template.team, self.team)

    def test_email_template_str_representation(self):
        """Test email template string representation."""
        template = EmailTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            type="campaign",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            created_by=self.owner,
        )
        self.assertEqual(str(template), "Test Template")


class TestCampaignModel(TestCase):
    """Test Campaign model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.template = EmailTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            type="campaign",
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            created_by=self.owner,
        )

    def test_campaign_creation(self):
        """Test campaign creation."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="draft",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            template=self.template,
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            created_by=self.owner,
        )
        self.assertEqual(campaign.name, "Test Campaign")
        self.assertEqual(campaign.status, "draft")
        self.assertEqual(campaign.team, self.team)

    def test_campaign_rate_calculations(self):
        """Test campaign rate calculations."""
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
            created_by=self.owner,
            emails_delivered=100,
            emails_opened=20,
            emails_clicked=5,
            emails_sent=100,
            emails_bounced=5,
        )

        self.assertEqual(campaign.open_rate, 20.0)
        self.assertEqual(campaign.click_rate, 5.0)
        self.assertEqual(campaign.bounce_rate, 5.0)

    def test_campaign_can_send(self):
        """Test campaign can_send method."""
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
            created_by=self.owner,
        )

        self.assertTrue(campaign.can_send())

        campaign.status = "sent"
        self.assertFalse(campaign.can_send())

    def test_campaign_is_scheduled(self):
        """Test campaign is_scheduled method."""
        future_time = timezone.now() + timedelta(hours=1)
        campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="scheduled",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            send_at=future_time,
            created_by=self.owner,
        )

        self.assertTrue(campaign.is_scheduled())

        campaign.send_at = timezone.now() - timedelta(hours=1)
        self.assertFalse(campaign.is_scheduled())


class TestSubscriberModel(TestCase):
    """Test Subscriber model functionality."""

    def test_subscriber_creation(self):
        """Test subscriber creation."""
        subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
            custom_fields={"company": "Test Corp"},
            timezone="UTC",
            preferred_language="en",
            gdpr_consent=True,
            gdpr_consent_date=timezone.now(),
        )
        self.assertEqual(subscriber.email, "test@example.com")
        self.assertEqual(subscriber.full_name, "John Doe")
        self.assertEqual(subscriber.status, "subscribed")

    def test_subscriber_full_name_property(self):
        """Test subscriber full_name property."""
        subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )
        self.assertEqual(subscriber.full_name, "John Doe")

        subscriber.first_name = ""
        subscriber.last_name = ""
        self.assertEqual(subscriber.full_name, "test@example.com")

    def test_subscriber_is_engaged(self):
        """Test subscriber is_engaged method."""
        subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
            engagement_score=0.6,
        )
        self.assertTrue(subscriber.is_engaged())

        subscriber.engagement_score = 0.3
        self.assertFalse(subscriber.is_engaged())


class TestEmailEventModel(TestCase):
    """Test EmailEvent model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="draft",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            created_by=self.owner,
        )
        self.subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )

    def test_email_event_creation(self):
        """Test email event creation."""
        event = EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-id",
            mailgun_event_id="test-event-id",
            recipient_email="test@example.com",
            subscriber=self.subscriber,
            campaign=self.campaign,
            user_agent="Mozilla/5.0 (Test Browser)",
            ip_address="192.168.1.1",
            device_type="desktop",
            country="US",
            raw_data={"test": "data"},
        )
        self.assertEqual(event.event_type, "opened")
        self.assertEqual(event.recipient_email, "test@example.com")
        self.assertEqual(event.subscriber, self.subscriber)
        self.assertEqual(event.campaign, self.campaign)

    def test_email_event_str_representation(self):
        """Test email event string representation."""
        event = EmailEvent.objects.create(
            event_type="opened",
            timestamp=timezone.now(),
            mailgun_message_id="test-message-id",
            mailgun_event_id="test-event-id",
            recipient_email="test@example.com",
            subscriber=self.subscriber,
            campaign=self.campaign,
        )
        expected_str = f"opened - test@example.com - {event.timestamp}"
        self.assertEqual(str(event), expected_str)


class TestAutomationWorkflowModel(TestCase):
    """Test AutomationWorkflow model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )

    def test_workflow_creation(self):
        """Test workflow creation."""
        workflow = AutomationWorkflow.objects.create(
            name="Test Workflow",
            description="Test workflow description",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            created_by=self.owner,
        )
        self.assertEqual(workflow.name, "Test Workflow")
        self.assertEqual(workflow.status, "active")
        self.assertEqual(workflow.team, self.team)

    def test_workflow_completion_rate(self):
        """Test workflow completion rate calculation."""
        workflow = AutomationWorkflow.objects.create(
            name="Test Workflow",
            description="Test workflow description",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            total_entries=100,
            completed_workflows=75,
            created_by=self.owner,
        )
        self.assertEqual(workflow.completion_rate, 75.0)

        workflow.total_entries = 0
        self.assertEqual(workflow.completion_rate, 0.0)


class TestWorkflowStepModel(TestCase):
    """Test WorkflowStep model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.workflow = AutomationWorkflow.objects.create(
            name="Test Workflow",
            description="Test workflow description",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            created_by=self.owner,
        )

    def test_workflow_step_creation(self):
        """Test workflow step creation."""
        step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Test Step",
            step_type="email",
            order=1,
            config={"template_id": 1, "subject": "Test Email"},
            is_active=True,
        )
        self.assertEqual(step.workflow, self.workflow)
        self.assertEqual(step.step_type, "email")
        self.assertEqual(step.order, 1)

    def test_workflow_step_completion_rate(self):
        """Test workflow step completion rate calculation."""
        step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Test Step",
            step_type="email",
            order=1,
            config={"template_id": 1, "subject": "Test Email"},
            subscribers_entered=100,
            subscribers_completed=80,
            is_active=True,
        )
        self.assertEqual(step.completion_rate, 80.0)

        step.subscribers_entered = 0
        self.assertEqual(step.completion_rate, 0.0)


class TestIntegrationModel(TestCase):
    """Test Integration model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )

    def test_integration_creation(self):
        """Test integration creation."""
        integration = Integration.objects.create(
            name="Test Mailgun Integration",
            provider="mailgun",
            status="active",
            config={"domain": "test.example.com"},
            credentials='{"api_key": "test-key"}',
            created_by=self.owner,
        )
        self.assertEqual(integration.name, "Test Mailgun Integration")
        self.assertEqual(integration.provider, "mailgun")
        self.assertEqual(integration.status, "active")

    def test_integration_encrypt_decrypt_credentials(self):
        """Test integration credentials encryption/decryption."""
        integration = Integration.objects.create(
            name="Test Integration",
            provider="mailgun",
            status="active",
            config={},
            created_by=self.owner,
        )

        test_credentials = {"api_key": "test-key", "domain": "test.com"}
        integration.encrypt_credentials(test_credentials)

        decrypted = integration.decrypt_credentials()
        self.assertEqual(decrypted, test_credentials)

    def test_integration_str_representation(self):
        """Test integration string representation."""
        integration = Integration.objects.create(
            name="Test Integration",
            provider="mailgun",
            status="active",
            config={},
            created_by=self.owner,
        )
        self.assertEqual(str(integration), "Test Integration (mailgun)")


class TestWebhookEndpointModel(TestCase):
    """Test WebhookEndpoint model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.integration = Integration.objects.create(
            name="Test Integration",
            provider="mailgun",
            status="active",
            config={},
            created_by=self.owner,
        )

    def test_webhook_endpoint_creation(self):
        """Test webhook endpoint creation."""
        endpoint = WebhookEndpoint.objects.create(
            name="Test Webhook",
            event_type="mailgun_delivery",
            url_path="test-webhook",
            integration=self.integration,
            secret_key="test-secret",
            verify_signature=True,
            is_active=True,
        )
        self.assertEqual(endpoint.name, "Test Webhook")
        self.assertEqual(endpoint.event_type, "mailgun_delivery")
        self.assertEqual(endpoint.integration, self.integration)

    def test_webhook_endpoint_success_rate(self):
        """Test webhook endpoint success rate calculation."""
        endpoint = WebhookEndpoint.objects.create(
            name="Test Webhook",
            event_type="mailgun_delivery",
            url_path="test-webhook",
            integration=self.integration,
            secret_key="test-secret",
            verify_signature=True,
            total_requests=100,
            successful_requests=95,
            is_active=True,
        )
        self.assertEqual(endpoint.success_rate, 95.0)

        endpoint.total_requests = 0
        self.assertEqual(endpoint.success_rate, 0.0)


class TestSyncJobModel(TestCase):
    """Test SyncJob model functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", username="owner", password="testpass123"
        )
        self.team = Team.objects.create(
            name="Test Team", description="Test team description", owner=self.owner
        )
        self.integration = Integration.objects.create(
            name="Test Integration",
            provider="odoo",
            status="active",
            config={},
            created_by=self.owner,
        )

    def test_sync_job_creation(self):
        """Test sync job creation."""
        job = SyncJob.objects.create(
            integration=self.integration,
            job_type="odoo_import_contacts",
            status="pending",
            config={"batch_size": 100},
            created_by=self.owner,
        )
        self.assertEqual(job.integration, self.integration)
        self.assertEqual(job.job_type, "odoo_import_contacts")
        self.assertEqual(job.status, "pending")

    def test_sync_job_progress_percentage(self):
        """Test sync job progress percentage calculation."""
        job = SyncJob.objects.create(
            integration=self.integration,
            job_type="odoo_import_contacts",
            status="running",
            total_records=100,
            processed_records=50,
            created_by=self.owner,
        )
        self.assertEqual(job.progress_percentage, 50.0)

        job.total_records = 0
        self.assertEqual(job.progress_percentage, 0.0)

    def test_sync_job_success_rate(self):
        """Test sync job success rate calculation."""
        job = SyncJob.objects.create(
            integration=self.integration,
            job_type="odoo_import_contacts",
            status="running",
            processed_records=100,
            successful_records=90,
            created_by=self.owner,
        )
        self.assertEqual(job.success_rate, 90.0)

        job.processed_records = 0
        self.assertEqual(job.success_rate, 0.0)

    def test_sync_job_duration(self):
        """Test sync job duration calculation."""
        start_time = timezone.now()
        job = SyncJob.objects.create(
            integration=self.integration,
            job_type="odoo_import_contacts",
            status="running",
            started_at=start_time,
            created_by=self.owner,
        )

        # Test with completed job
        job.completed_at = start_time + timedelta(hours=2)
        duration = job.duration()
        self.assertEqual(duration.total_seconds(), 7200)  # 2 hours

        # Test with running job
        job.completed_at = None
        job.status = "running"
        duration = job.duration()
        self.assertIsNotNone(duration)
        self.assertGreater(duration.total_seconds(), 0)


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestModelRelationships:
    """Test model relationships and constraints."""

    def test_team_user_relationship(self, team, user):
        """Test team-user relationship through membership."""
        from apps.accounts.models import TeamMembership

        membership = TeamMembership.objects.create(team=team, user=user, role="admin")

        assert membership.team == team
        assert membership.user == user
        assert membership.role == "admin"

    def test_campaign_subscriber_list_relationship(self, campaign, subscriber_list):
        """Test campaign-subscriber list many-to-many relationship."""
        campaign.subscriber_lists.add(subscriber_list)

        assert subscriber_list in campaign.subscriber_lists.all()
        assert campaign in subscriber_list.campaigns.all()

    def test_subscriber_tag_relationship(self, subscriber):
        """Test subscriber-tag many-to-many relationship."""
        from apps.subscribers.models import Tag

        tag = Tag.objects.create(name="Test Tag", color="#FF0000", team=subscriber.team)
        subscriber.tags.add(tag)

        assert tag in subscriber.tags.all()
        assert subscriber in tag.subscribers.all()

    def test_workflow_step_relationship(self, automation_workflow, workflow_step):
        """Test workflow-step relationship."""
        assert workflow_step.workflow == automation_workflow
        assert workflow_step in automation_workflow.steps.all()

    def test_email_event_campaign_relationship(self, email_event, campaign):
        """Test email event-campaign relationship."""
        assert email_event.campaign == campaign
        assert email_event in campaign.email_events.all()

    def test_webhook_log_endpoint_relationship(self, webhook_endpoint):
        """Test webhook log-endpoint relationship."""
        from apps.integrations.models import WebhookLog

        log = WebhookLog.objects.create(
            webhook_endpoint=webhook_endpoint,
            request_id="test-request-123",
            status="success",
            headers={"Content-Type": "application/json"},
            payload={"test": "data"},
            response_status=200,
        )

        assert log.webhook_endpoint == webhook_endpoint
        assert log in webhook_endpoint.logs.all()


@pytest.mark.django_db
class TestModelValidation:
    """Test model validation and constraints."""

    def test_user_email_validation(self):
        """Test user email validation."""
        # Valid email
        user = User.objects.create_user(
            email="valid@example.com", username="validuser", password="testpass123"
        )
        assert user.email == "valid@example.com"

    def test_subscriber_email_validation(self):
        """Test subscriber email validation."""
        from apps.subscribers.models import Subscriber

        # Valid email
        subscriber = Subscriber.objects.create(
            email="valid@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )
        assert subscriber.email == "valid@example.com"

    def test_campaign_status_choices(self):
        """Test campaign status choices validation."""
        from apps.campaigns.models import Campaign

        valid_statuses = [
            "draft",
            "scheduled",
            "sending",
            "sent",
            "paused",
            "cancelled",
        ]

        for status in valid_statuses:
            campaign = Campaign.objects.create(
                name=f"Test Campaign {status}",
                description="Test description",
                type="regular",
                status=status,
                team=None,  # Will be set by fixture
                subject="Test Subject",
                from_email="test@example.com",
                from_name="Test Sender",
                html_content="<h1>Test</h1>",
                text_content="Test",
                created_by=None,  # Will be set by fixture
            )
            assert campaign.status == status

    def test_workflow_trigger_type_choices(self):
        """Test workflow trigger type choices validation."""
        from apps.automation.models import AutomationWorkflow

        valid_triggers = [
            "subscriber_added",
            "tag_added",
            "email_opened",
            "email_clicked",
            "date_based",
            "custom_event",
            "api_trigger",
        ]

        for trigger in valid_triggers:
            workflow = AutomationWorkflow.objects.create(
                name=f"Test Workflow {trigger}",
                description="Test description",
                status="active",
                team=None,  # Will be set by fixture
                trigger_type=trigger,
                trigger_config={},
                entry_conditions=[],
                exit_conditions=[],
                created_by=None,  # Will be set by fixture
            )
            assert workflow.trigger_type == trigger
