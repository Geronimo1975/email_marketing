"""
Comprehensive Celery task tests for Email Marketing Platform.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from apps.campaigns.tasks import (
    send_campaign_task,
    process_regular_campaign,
    process_ab_test_campaign,
    process_scheduled_campaigns,
)
from apps.subscribers.tasks import (
    import_subscribers_task,
    export_subscribers_task,
    update_engagement_scores,
    cleanup_inactive_subscribers,
)
from apps.automation.tasks import (
    execute_workflow_task,
    process_workflow_step,
    process_workflow_triggers,
    cleanup_completed_workflows,
)
from apps.integrations.tasks import (
    sync_odoo_contacts,
    sync_mailgun_suppressions,
    cleanup_old_webhook_logs,
    sync_subscriber_to_odoo,
)

# Analytics tasks are not implemented yet


class TestCampaignTasks(TestCase):
    """Test campaign-related Celery tasks."""

    def setUp(self):
        from apps.accounts.models import User, Team
        from apps.campaigns.models import Campaign, EmailTemplate
        from apps.subscribers.models import SubscriberList, Subscriber

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
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            created_by=self.user,
        )

        # Create test subscriber list
        self.subscriber_list = SubscriberList.objects.create(
            name="Test List",
            description="Test subscriber list",
            created_by=self.user,
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
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
            created_by=self.user,
        )
        self.campaign.subscriber_lists.add(self.subscriber_list)

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

    @patch("apps.campaigns.tasks.send_campaign_email_task.delay")
    def test_send_campaign_task_success(self, mock_send_email):
        """Test successful campaign sending task."""
        mock_send_email.return_value = Mock(id="test-task-id")

        result = send_campaign_task(self.campaign.id)
        self.assertEqual(result, "Campaign sent successfully")
        self.assertEqual(mock_send_email.call_count, 2)  # 2 subscribers

    @patch("apps.campaigns.tasks.send_campaign_email_task.delay")
    def test_send_campaign_task_campaign_not_found(self, mock_send_email):
        """Test campaign sending task with non-existent campaign."""
        result = send_campaign_task(999)
        self.assertEqual(result, "Campaign not found")
        mock_send_email.assert_not_called()

    @patch("apps.campaigns.tasks.send_campaign_email_task.delay")
    def test_send_campaign_task_campaign_already_sent(self, mock_send_email):
        """Test campaign sending task with already sent campaign."""
        self.campaign.status = "sent"
        self.campaign.save()

        result = send_campaign_task(self.campaign.id)
        self.assertEqual(result, "Campaign already sent")
        mock_send_email.assert_not_called()

    @patch("apps.integrations.services.MailgunService")
    def test_send_campaign_email_task_success(self, mock_mailgun_class):
        """Test successful campaign email sending task."""
        mock_mailgun = Mock()
        mock_mailgun.send_email.return_value = {"id": "test-message-id"}
        mock_mailgun_class.return_value = mock_mailgun

        result = send_campaign_email_task(
            self.campaign.id, self.subscriber1.id, "subscriber1@example.com"
        )
        self.assertEqual(result, "Email sent successfully")
        mock_mailgun.send_email.assert_called_once()

    @patch("apps.integrations.services.MailgunService")
    def test_send_campaign_email_task_failure(self, mock_mailgun_class):
        """Test campaign email sending task failure."""
        mock_mailgun = Mock()
        mock_mailgun.send_email.side_effect = Exception("API Error")
        mock_mailgun_class.return_value = mock_mailgun

        result = send_campaign_email_task(
            self.campaign.id, self.subscriber1.id, "subscriber1@example.com"
        )
        self.assertEqual(result, "Failed to send email: API Error")

    def test_send_campaign_email_task_campaign_not_found(self):
        """Test campaign email sending task with non-existent campaign."""
        result = send_campaign_email_task(999, self.subscriber1.id, "test@example.com")
        self.assertEqual(result, "Campaign not found")

    def test_send_campaign_email_task_subscriber_not_found(self):
        """Test campaign email sending task with non-existent subscriber."""
        result = send_campaign_email_task(self.campaign.id, 999, "test@example.com")
        self.assertEqual(result, "Subscriber not found")

    @patch("apps.campaigns.tasks.send_campaign_task.delay")
    def test_schedule_campaign_task_success(self, mock_send_campaign):
        """Test successful campaign scheduling task."""
        mock_send_campaign.return_value = Mock(id="test-task-id")

        future_time = timezone.now() + timedelta(hours=1)
        self.campaign.send_at = future_time
        self.campaign.status = "scheduled"
        self.campaign.save()

        result = schedule_campaign_task(self.campaign.id)
        self.assertEqual(result, "Campaign scheduled successfully")

    def test_schedule_campaign_task_campaign_not_found(self):
        """Test campaign scheduling task with non-existent campaign."""
        result = schedule_campaign_task(999)
        self.assertEqual(result, "Campaign not found")

    def test_schedule_campaign_task_campaign_not_scheduled(self):
        """Test campaign scheduling task with non-scheduled campaign."""
        result = schedule_campaign_task(self.campaign.id)
        self.assertEqual(result, "Campaign is not scheduled")

    @patch("apps.campaigns.tasks.send_campaign_email_task.delay")
    def test_process_campaign_recipients_task_success(self, mock_send_email):
        """Test successful campaign recipients processing task."""
        mock_send_email.return_value = Mock(id="test-task-id")

        result = process_campaign_recipients_task(
            self.campaign.id, [self.subscriber1.id, self.subscriber2.id]
        )
        self.assertEqual(result, "Recipients processed successfully")
        self.assertEqual(mock_send_email.call_count, 2)

    def test_process_campaign_recipients_task_campaign_not_found(self):
        """Test campaign recipients processing task with non-existent campaign."""
        result = process_campaign_recipients_task(999, [self.subscriber1.id])
        self.assertEqual(result, "Campaign not found")


class TestSubscriberTasks(TestCase):
    """Test subscriber-related Celery tasks."""

    def setUp(self):
        from apps.accounts.models import User, Team
        from apps.subscribers.models import SubscriberList

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

    @patch("apps.subscribers.tasks.process_subscriber_import")
    def test_import_subscribers_task_success(self, mock_process_import):
        """Test successful subscriber import task."""
        mock_process_import.return_value = {"imported": 5, "updated": 2, "errors": 0}

        csv_data = """email,first_name,last_name,company
john@example.com,John,Doe,Acme Corp
jane@example.com,Jane,Smith,Tech Inc"""

        result = import_subscribers_task(
            csv_data,
            self.subscriber_list.id,
            update_existing=True,
            skip_duplicates=True,
        )
        self.assertEqual(result, "Subscribers imported successfully")
        mock_process_import.assert_called_once()

    def test_import_subscribers_task_list_not_found(self):
        """Test subscriber import task with non-existent list."""
        result = import_subscribers_task("csv_data", 999)
        self.assertEqual(result, "Subscriber list not found")

    @patch("apps.subscribers.tasks.process_subscriber_export")
    def test_export_subscribers_task_success(self, mock_process_export):
        """Test successful subscriber export task."""
        mock_process_export.return_value = "export_file.csv"

        result = export_subscribers_task(
            self.subscriber_list.id, "csv", ["email", "first_name", "last_name"]
        )
        self.assertEqual(result, "Subscribers exported successfully")
        mock_process_export.assert_called_once()

    def test_export_subscribers_task_list_not_found(self):
        """Test subscriber export task with non-existent list."""
        result = export_subscribers_task(999, "csv")
        self.assertEqual(result, "Subscriber list not found")

    @patch("apps.subscribers.tasks.calculate_subscriber_engagement")
    def test_update_subscriber_engagement_task_success(self, mock_calculate):
        """Test successful subscriber engagement update task."""
        mock_calculate.return_value = 0.8

        from apps.subscribers.models import Subscriber

        subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )

        result = update_subscriber_engagement_task(subscriber.id)
        self.assertEqual(result, "Engagement updated successfully")
        mock_calculate.assert_called_once_with(subscriber)

    def test_update_subscriber_engagement_task_subscriber_not_found(self):
        """Test subscriber engagement update task with non-existent subscriber."""
        result = update_subscriber_engagement_task(999)
        self.assertEqual(result, "Subscriber not found")

    @patch("apps.subscribers.tasks.cleanup_subscriber_data")
    def test_cleanup_unsubscribed_task_success(self, mock_cleanup):
        """Test successful unsubscribed cleanup task."""
        mock_cleanup.return_value = 5

        result = cleanup_unsubscribed_task(days=30)
        self.assertEqual(result, "Cleanup completed successfully")
        mock_cleanup.assert_called_once_with(30)

    def test_cleanup_unsubscribed_task_invalid_days(self):
        """Test unsubscribed cleanup task with invalid days parameter."""
        result = cleanup_unsubscribed_task(days=-1)
        self.assertEqual(result, "Invalid days parameter")


class TestAutomationTasks(TestCase):
    """Test automation-related Celery tasks."""

    def setUp(self):
        from apps.accounts.models import User, Team
        from apps.automation.models import AutomationWorkflow, WorkflowStep
        from apps.subscribers.models import Subscriber

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

        # Create test workflow
        self.workflow = AutomationWorkflow.objects.create(
            name="Test Workflow",
            description="Test workflow description",
            status="active",
            trigger_type="subscriber_added",
            trigger_config={"list_id": 1},
            entry_conditions=[],
            exit_conditions=[],
            created_by=self.user,
        )

        # Create test workflow step
        self.workflow_step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Test Step",
            step_type="email",
            order=1,
            config={"template_id": 1, "subject": "Test Email"},
            is_active=True,
        )

        # Create test subscriber
        self.subscriber = Subscriber.objects.create(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            status="subscribed",
        )

    @patch("apps.automation.tasks.process_workflow_step_task.delay")
    def test_execute_workflow_task_success(self, mock_process_step):
        """Test successful workflow execution task."""
        mock_process_step.return_value = Mock(id="test-task-id")

        result = execute_workflow_task(
            self.workflow.id, self.subscriber.id, {"test": "data"}
        )
        self.assertEqual(result, "Workflow executed successfully")
        mock_process_step.assert_called_once()

    def test_execute_workflow_task_workflow_not_found(self):
        """Test workflow execution task with non-existent workflow."""
        result = execute_workflow_task(999, self.subscriber.id, {})
        self.assertEqual(result, "Workflow not found")

    def test_execute_workflow_task_subscriber_not_found(self):
        """Test workflow execution task with non-existent subscriber."""
        result = execute_workflow_task(self.workflow.id, 999, {})
        self.assertEqual(result, "Subscriber not found")

    def test_execute_workflow_task_workflow_inactive(self):
        """Test workflow execution task with inactive workflow."""
        self.workflow.status = "inactive"
        self.workflow.save()

        result = execute_workflow_task(self.workflow.id, self.subscriber.id, {})
        self.assertEqual(result, "Workflow is not active")

    @patch("apps.automation.tasks.execute_workflow_action")
    def test_process_workflow_step_task_success(self, mock_execute_action):
        """Test successful workflow step processing task."""
        mock_execute_action.return_value = True

        result = process_workflow_step_task(
            self.workflow_step.id, self.subscriber.id, {"test": "data"}
        )
        self.assertEqual(result, "Step processed successfully")
        mock_execute_action.assert_called_once()

    def test_process_workflow_step_task_step_not_found(self):
        """Test workflow step processing task with non-existent step."""
        result = process_workflow_step_task(999, self.subscriber.id, {})
        self.assertEqual(result, "Workflow step not found")

    def test_process_workflow_step_task_subscriber_not_found(self):
        """Test workflow step processing task with non-existent subscriber."""
        result = process_workflow_step_task(self.workflow_step.id, 999, {})
        self.assertEqual(result, "Subscriber not found")

    def test_process_workflow_step_task_step_inactive(self):
        """Test workflow step processing task with inactive step."""
        self.workflow_step.is_active = False
        self.workflow_step.save()

        result = process_workflow_step_task(
            self.workflow_step.id, self.subscriber.id, {}
        )
        self.assertEqual(result, "Workflow step is not active")

    @patch("apps.automation.tasks.check_workflow_conditions")
    def test_check_workflow_conditions_task_success(self, mock_check_conditions):
        """Test successful workflow conditions checking task."""
        mock_check_conditions.return_value = True

        result = check_workflow_conditions_task(
            self.workflow.id, self.subscriber.id, {"test": "data"}
        )
        self.assertEqual(result, "Conditions checked successfully")
        mock_check_conditions.assert_called_once()

    def test_check_workflow_conditions_task_workflow_not_found(self):
        """Test workflow conditions checking task with non-existent workflow."""
        result = check_workflow_conditions_task(999, self.subscriber.id, {})
        self.assertEqual(result, "Workflow not found")

    def test_check_workflow_conditions_task_subscriber_not_found(self):
        """Test workflow conditions checking task with non-existent subscriber."""
        result = check_workflow_conditions_task(self.workflow.id, 999, {})
        self.assertEqual(result, "Subscriber not found")

    @patch("apps.automation.tasks.cleanup_workflow_data")
    def test_cleanup_completed_workflows_task_success(self, mock_cleanup):
        """Test successful completed workflows cleanup task."""
        mock_cleanup.return_value = 3

        result = cleanup_completed_workflows_task(days=30)
        self.assertEqual(result, "Cleanup completed successfully")
        mock_cleanup.assert_called_once_with(30)

    def test_cleanup_completed_workflows_task_invalid_days(self):
        """Test completed workflows cleanup task with invalid days parameter."""
        result = cleanup_completed_workflows_task(days=-1)
        self.assertEqual(result, "Invalid days parameter")


class TestIntegrationTasks(TestCase):
    """Test integration-related Celery tasks."""

    def setUp(self):
        from apps.accounts.models import User, Team
        from apps.integrations.models import Integration

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

        # Create test integration
        self.integration = Integration.objects.create(
            name="Test Integration",
            provider="odoo",
            status="active",
            config={"url": "https://test.odoo.com"},
            credentials='{"api_key": "test-key"}',
            created_by=self.user,
        )

    @patch("apps.integrations.tasks.sync_odoo_contacts_data")
    def test_sync_odoo_contacts_task_success(self, mock_sync_data):
        """Test successful Odoo contacts sync task."""
        mock_sync_data.return_value = {"imported": 10, "updated": 5, "errors": 0}

        result = sync_odoo_contacts_task(self.integration.id)
        self.assertEqual(result, "Contacts synced successfully")
        mock_sync_data.assert_called_once()

    def test_sync_odoo_contacts_task_integration_not_found(self):
        """Test Odoo contacts sync task with non-existent integration."""
        result = sync_odoo_contacts_task(999)
        self.assertEqual(result, "Integration not found")

    def test_sync_odoo_contacts_task_integration_inactive(self):
        """Test Odoo contacts sync task with inactive integration."""
        self.integration.status = "inactive"
        self.integration.save()

        result = sync_odoo_contacts_task(self.integration.id)
        self.assertEqual(result, "Integration is not active")

    @patch("apps.integrations.tasks.process_webhook_data")
    def test_process_webhook_task_success(self, mock_process_data):
        """Test successful webhook processing task."""
        mock_process_data.return_value = True

        webhook_data = {"event": "test", "data": {}}
        result = process_webhook_task("mailgun", webhook_data)
        self.assertEqual(result, "Webhook processed successfully")
        mock_process_data.assert_called_once()

    def test_process_webhook_task_invalid_provider(self):
        """Test webhook processing task with invalid provider."""
        webhook_data = {"event": "test", "data": {}}
        result = process_webhook_task("invalid", webhook_data)
        self.assertEqual(result, "Unsupported webhook provider")

    @patch("apps.integrations.tasks.validate_email_addresses")
    def test_validate_emails_task_success(self, mock_validate):
        """Test successful email validation task."""
        mock_validate.return_value = {"valid": 8, "invalid": 2}

        email_list = ["test1@example.com", "test2@example.com"]
        result = validate_emails_task(email_list)
        self.assertEqual(result, "Emails validated successfully")
        mock_validate.assert_called_once()

    def test_validate_emails_task_empty_list(self):
        """Test email validation task with empty list."""
        result = validate_emails_task([])
        self.assertEqual(result, "No emails to validate")

    @patch("apps.integrations.tasks.update_suppression_data")
    def test_update_suppression_lists_task_success(self, mock_update):
        """Test successful suppression lists update task."""
        mock_update.return_value = {"bounces": 5, "complaints": 2}

        result = update_suppression_lists_task()
        self.assertEqual(result, "Suppression lists updated successfully")
        mock_update.assert_called_once()


class TestAnalyticsTasks(TestCase):
    """Test analytics-related Celery tasks."""

    def setUp(self):
        from apps.accounts.models import User, Team
        from apps.campaigns.models import Campaign

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
            name="Test Campaign",
            description="Test campaign description",
            type="regular",
            status="sent",
            subject="Test Campaign Subject",
            from_email="test@example.com",
            from_name="Test Sender",
            html_content="<h1>Test Campaign HTML</h1>",
            text_content="Test Campaign Text",
            created_by=self.user,
        )

    @patch("apps.analytics.tasks.generate_campaign_report_data")
    def test_generate_campaign_report_task_success(self, mock_generate):
        """Test successful campaign report generation task."""
        mock_generate.return_value = {"report_id": "test-report-id"}

        result = generate_campaign_report_task(
            self.campaign.id, "2024-01-01", "2024-01-31"
        )
        self.assertEqual(result, "Report generated successfully")
        mock_generate.assert_called_once()

    def test_generate_campaign_report_task_campaign_not_found(self):
        """Test campaign report generation task with non-existent campaign."""
        result = generate_campaign_report_task(999, "2024-01-01", "2024-01-31")
        self.assertEqual(result, "Campaign not found")

    @patch("apps.analytics.tasks.update_analytics_data")
    def test_update_analytics_task_success(self, mock_update):
        """Test successful analytics update task."""
        mock_update.return_value = {"updated": 100}

        result = update_analytics_task()
        self.assertEqual(result, "Analytics updated successfully")
        mock_update.assert_called_once()

    @patch("apps.analytics.tasks.cleanup_old_events_data")
    def test_cleanup_old_events_task_success(self, mock_cleanup):
        """Test successful old events cleanup task."""
        mock_cleanup.return_value = 50

        result = cleanup_old_events_task(days=90)
        self.assertEqual(result, "Cleanup completed successfully")
        mock_cleanup.assert_called_once()

    def test_cleanup_old_events_task_invalid_days(self):
        """Test old events cleanup task with invalid days parameter."""
        result = cleanup_old_events_task(days=-1)
        self.assertEqual(result, "Invalid days parameter")

    @patch("apps.analytics.tasks.calculate_engagement_metrics_data")
    def test_calculate_engagement_metrics_task_success(self, mock_calculate):
        """Test successful engagement metrics calculation task."""
        mock_calculate.return_value = {"metrics_updated": 25}

        result = calculate_engagement_metrics_task()
        self.assertEqual(result, "Metrics calculated successfully")
        mock_calculate.assert_called_once()


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestTaskIntegration:
    """Test task integration with models and services."""

    def test_send_campaign_task_with_mailgun(
        self, campaign, subscriber, mock_mailgun_service
    ):
        """Test send campaign task integration with Mailgun service."""
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service_class.return_value = mock_mailgun_service

            result = send_campaign_task(campaign.id)
            assert result == "Campaign sent successfully"

    def test_import_subscribers_task_with_csv(self, subscriber_list, sample_csv_data):
        """Test import subscribers task with CSV data."""
        with patch("apps.subscribers.tasks.process_subscriber_import") as mock_process:
            mock_process.return_value = {"imported": 3, "updated": 0, "errors": 0}

            result = import_subscribers_task(
                sample_csv_data, subscriber_list.id, update_existing=True
            )
            assert result == "Subscribers imported successfully"

    def test_execute_workflow_task_with_automation(
        self, automation_workflow, subscriber
    ):
        """Test execute workflow task with automation workflow."""
        with patch(
            "apps.automation.tasks.process_workflow_step_task.delay"
        ) as mock_process:
            mock_process.return_value = Mock(id="test-task-id")

            result = execute_workflow_task(
                automation_workflow.id, subscriber.id, {"test": "data"}
            )
            assert result == "Workflow executed successfully"

    def test_sync_odoo_contacts_task_with_integration(
        self, integration, mock_odoo_service
    ):
        """Test sync Odoo contacts task with integration."""
        with patch("apps.integrations.services.OdooService") as mock_service_class:
            mock_service_class.return_value = mock_odoo_service

            with patch("apps.integrations.tasks.sync_odoo_contacts_data") as mock_sync:
                mock_sync.return_value = {"imported": 5, "updated": 2, "errors": 0}

                result = sync_odoo_contacts_task(integration.id)
                assert result == "Contacts synced successfully"

    def test_generate_campaign_report_task_with_campaign(self, campaign):
        """Test generate campaign report task with campaign."""
        with patch(
            "apps.analytics.tasks.generate_campaign_report_data"
        ) as mock_generate:
            mock_generate.return_value = {"report_id": "test-report-id"}

            result = generate_campaign_report_task(
                campaign.id, "2024-01-01", "2024-01-31"
            )
            assert result == "Report generated successfully"


@pytest.mark.django_db
class TestTaskErrorHandling:
    """Test task error handling and recovery."""

    def test_send_campaign_task_database_error(self):
        """Test send campaign task with database error."""
        with patch("apps.campaigns.models.Campaign.objects.get") as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = send_campaign_task(1)
            assert result == "Database error"

    def test_import_subscribers_task_processing_error(self, subscriber_list):
        """Test import subscribers task with processing error."""
        with patch("apps.subscribers.tasks.process_subscriber_import") as mock_process:
            mock_process.side_effect = Exception("Processing error")

            result = import_subscribers_task("csv_data", subscriber_list.id)
            assert result == "Processing error"

    def test_execute_workflow_task_workflow_error(self, subscriber):
        """Test execute workflow task with workflow error."""
        with patch("apps.automation.models.AutomationWorkflow.objects.get") as mock_get:
            mock_get.side_effect = Exception("Workflow error")

            result = execute_workflow_task(1, subscriber.id, {})
            assert result == "Workflow error"

    def test_sync_odoo_contacts_task_integration_error(self):
        """Test sync Odoo contacts task with integration error."""
        with patch("apps.integrations.models.Integration.objects.get") as mock_get:
            mock_get.side_effect = Exception("Integration error")

            result = sync_odoo_contacts_task(1)
            assert result == "Integration error"

    def test_generate_campaign_report_task_analytics_error(self):
        """Test generate campaign report task with analytics error."""
        with patch("apps.campaigns.models.Campaign.objects.get") as mock_get:
            mock_get.side_effect = Exception("Analytics error")

            result = generate_campaign_report_task(1, "2024-01-01", "2024-01-31")
            assert result == "Analytics error"


@pytest.mark.django_db
class TestTaskRetryMechanisms:
    """Test task retry mechanisms and resilience."""

    def test_send_campaign_email_task_retry(self, campaign, subscriber):
        """Test send campaign email task retry mechanism."""
        with patch("apps.integrations.services.MailgunService") as mock_service_class:
            mock_service = Mock()
            mock_service.send_email.side_effect = Exception("Temporary API error")
            mock_service_class.return_value = mock_service

            # Task should raise exception for retry
            with pytest.raises(Exception):
                send_campaign_email_task(campaign.id, subscriber.id, "test@example.com")

    def test_import_subscribers_task_retry(self, subscriber_list):
        """Test import subscribers task retry mechanism."""
        with patch("apps.subscribers.tasks.process_subscriber_import") as mock_process:
            mock_process.side_effect = Exception("Temporary processing error")

            # Task should raise exception for retry
            with pytest.raises(Exception):
                import_subscribers_task("csv_data", subscriber_list.id)

    def test_sync_odoo_contacts_task_retry(self, integration):
        """Test sync Odoo contacts task retry mechanism."""
        with patch("apps.integrations.tasks.sync_odoo_contacts_data") as mock_sync:
            mock_sync.side_effect = Exception("Temporary sync error")

            # Task should raise exception for retry
            with pytest.raises(Exception):
                sync_odoo_contacts_task(integration.id)


@pytest.mark.django_db
class TestTaskPerformance:
    """Test task performance and optimization."""

    def test_send_campaign_task_bulk_processing(self, campaign, subscriber_list):
        """Test send campaign task bulk processing performance."""
        # Create multiple subscribers
        from apps.subscribers.models import Subscriber

        subscribers = []
        for i in range(10):
            subscriber = Subscriber.objects.create(
                email=f"subscriber{i}@example.com",
                first_name=f"User{i}",
                last_name="Test",
                status="subscribed",
                team=campaign.team,
            )
            subscribers.append(subscriber)
            subscriber_list.subscribers.add(subscriber)

        with patch(
            "apps.campaigns.tasks.send_campaign_email_task.delay"
        ) as mock_send_email:
            mock_send_email.return_value = Mock(id="test-task-id")

            result = send_campaign_task(campaign.id)
            assert result == "Campaign sent successfully"
            assert mock_send_email.call_count == 10

    def test_import_subscribers_task_large_dataset(self, subscriber_list):
        """Test import subscribers task with large dataset."""
        # Simulate large CSV data
        large_csv_data = "\n".join(
            [f"user{i}@example.com,User{i},Test,Company{i}" for i in range(1000)]
        )

        with patch("apps.subscribers.tasks.process_subscriber_import") as mock_process:
            mock_process.return_value = {"imported": 1000, "updated": 0, "errors": 0}

            result = import_subscribers_task(
                large_csv_data, subscriber_list.id, update_existing=True
            )
            assert result == "Subscribers imported successfully"

    def test_cleanup_tasks_performance(self):
        """Test cleanup tasks performance."""
        with patch("apps.subscribers.tasks.cleanup_subscriber_data") as mock_cleanup:
            mock_cleanup.return_value = 100

            result = cleanup_unsubscribed_task(days=30)
            assert result == "Cleanup completed successfully"
            mock_cleanup.assert_called_once_with(30)
