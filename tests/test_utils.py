"""
Comprehensive utility function tests for Email Marketing Platform.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
import io

from apps.campaigns.utils import (
    get_campaign_stats,
    calculate_engagement_metrics,
    get_campaign_performance_comparison,
    get_campaign_trends,
    get_top_performing_campaigns,
    get_campaign_health_score,
    validate_campaign_before_sending,
)
from apps.subscribers.utils import (
    get_subscriber_stats,
    calculate_engagement_score,
    segment_subscribers,
    get_subscriber_engagement_trends,
    get_top_engaged_subscribers,
    get_subscriber_health_score,
    validate_subscriber_data,
    process_subscriber_import,
    export_subscribers_to_csv,
)
from apps.analytics.utils import (
    get_dashboard_stats,
    get_campaign_performance,
    get_subscriber_engagement,
    get_email_metrics,
    get_click_analytics,
    get_delivery_analytics,
    get_engagement_timeline,
    get_top_performing_campaigns,
)
from apps.automation.utils import (
    execute_workflow,
    validate_workflow_conditions,
    get_workflow_stats,
    get_subscriber_workflows,
    trigger_workflow_for_subscriber,
    pause_workflow,
    resume_workflow,
    get_workflow_performance,
)

# Integration utils are not implemented yet


class TestCampaignUtils(TestCase):
    """Test campaign utility functions."""

    def test_calculate_campaign_metrics(self):
        """Test campaign metrics calculation."""
        metrics = calculate_campaign_metrics(
            emails_sent=100,
            emails_delivered=95,
            emails_opened=20,
            emails_clicked=5,
            emails_bounced=3,
            emails_complained=1,
        )

        self.assertEqual(metrics["delivery_rate"], 95.0)
        self.assertEqual(metrics["open_rate"], 21.05)  # 20/95 * 100
        self.assertEqual(metrics["click_rate"], 5.26)  # 5/95 * 100
        self.assertEqual(metrics["bounce_rate"], 3.0)
        self.assertEqual(metrics["complaint_rate"], 1.0)

    def test_calculate_campaign_metrics_zero_division(self):
        """Test campaign metrics calculation with zero division."""
        metrics = calculate_campaign_metrics(
            emails_sent=0,
            emails_delivered=0,
            emails_opened=0,
            emails_clicked=0,
            emails_bounced=0,
            emails_complained=0,
        )

        self.assertEqual(metrics["delivery_rate"], 0.0)
        self.assertEqual(metrics["open_rate"], 0.0)
        self.assertEqual(metrics["click_rate"], 0.0)
        self.assertEqual(metrics["bounce_rate"], 0.0)
        self.assertEqual(metrics["complaint_rate"], 0.0)

    def test_generate_campaign_preview(self):
        """Test campaign preview generation."""
        campaign_data = {
            "subject": "Test Subject",
            "html_content": "<h1>Hello {{first_name}}</h1>",
            "text_content": "Hello {{first_name}}",
            "from_name": "Test Sender",
            "from_email": "test@example.com",
        }

        preview = generate_campaign_preview(
            campaign_data, {"first_name": "John", "last_name": "Doe"}
        )

        self.assertIn("Hello John", preview["html_content"])
        self.assertIn("Hello John", preview["text_content"])
        self.assertEqual(preview["subject"], "Test Subject")

    def test_validate_campaign_data(self):
        """Test campaign data validation."""
        valid_data = {
            "name": "Test Campaign",
            "subject": "Test Subject",
            "from_email": "test@example.com",
            "from_name": "Test Sender",
            "html_content": "<h1>Test</h1>",
            "text_content": "Test",
        }

        result = validate_campaign_data(valid_data)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_campaign_data_invalid(self):
        """Test campaign data validation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "subject": "",  # Empty subject
            "from_email": "invalid-email",  # Invalid email
            "from_name": "",  # Empty from name
            "html_content": "",  # Empty content
            "text_content": "",  # Empty content
        }

        result = validate_campaign_data(invalid_data)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_process_campaign_recipients(self):
        """Test campaign recipients processing."""
        recipients = [
            {"email": "test1@example.com", "first_name": "John"},
            {"email": "test2@example.com", "first_name": "Jane"},
            {"email": "test3@example.com", "first_name": "Bob"},
        ]

        processed = process_campaign_recipients(recipients)
        self.assertEqual(len(processed), 3)
        self.assertEqual(processed[0]["email"], "test1@example.com")

    def test_calculate_ab_test_winner(self):
        """Test A/B test winner calculation."""
        variant_a = {"emails_sent": 100, "emails_opened": 20, "emails_clicked": 5}
        variant_b = {"emails_sent": 100, "emails_opened": 25, "emails_clicked": 8}

        winner = calculate_ab_test_winner(variant_a, variant_b)
        self.assertEqual(winner["winner"], "B")
        self.assertGreater(winner["confidence"], 0.5)

    def test_generate_campaign_report(self):
        """Test campaign report generation."""
        campaign_data = {
            "name": "Test Campaign",
            "emails_sent": 100,
            "emails_delivered": 95,
            "emails_opened": 20,
            "emails_clicked": 5,
        }

        report = generate_campaign_report(campaign_data)
        self.assertIn("campaign_name", report)
        self.assertIn("metrics", report)
        self.assertIn("summary", report)


class TestSubscriberUtils(TestCase):
    """Test subscriber utility functions."""

    def test_validate_email_address_valid(self):
        """Test email address validation with valid email."""
        result = validate_email_address("test@example.com")
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["email"], "test@example.com")

    def test_validate_email_address_invalid(self):
        """Test email address validation with invalid email."""
        result = validate_email_address("invalid-email")
        self.assertFalse(result["is_valid"])
        self.assertIn("error", result)

    def test_validate_email_address_empty(self):
        """Test email address validation with empty email."""
        result = validate_email_address("")
        self.assertFalse(result["is_valid"])
        self.assertIn("error", result)

    def test_process_subscriber_import(self):
        """Test subscriber import processing."""
        csv_data = """email,first_name,last_name,company
john@example.com,John,Doe,Acme Corp
jane@example.com,Jane,Smith,Tech Inc
bob@example.com,Bob,Johnson,Data Co"""

        result = process_subscriber_import(csv_data, update_existing=True)
        self.assertEqual(result["imported"], 3)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["errors"], 0)

    def test_process_subscriber_import_with_errors(self):
        """Test subscriber import processing with errors."""
        csv_data = """email,first_name,last_name,company
invalid-email,John,Doe,Acme Corp
jane@example.com,Jane,Smith,Tech Inc
bob@example.com,Bob,Johnson,Data Co"""

        result = process_subscriber_import(csv_data, update_existing=True)
        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["errors"], 1)

    def test_process_subscriber_export(self):
        """Test subscriber export processing."""
        subscribers = [
            {"email": "test1@example.com", "first_name": "John", "last_name": "Doe"},
            {"email": "test2@example.com", "first_name": "Jane", "last_name": "Smith"},
        ]

        result = process_subscriber_export(subscribers, "csv")
        self.assertIn("csv", result)
        self.assertIn("test1@example.com", result["csv"])

    def test_calculate_subscriber_engagement(self):
        """Test subscriber engagement calculation."""
        engagement_data = {
            "emails_opened": 10,
            "emails_clicked": 5,
            "emails_sent": 20,
            "last_activity": timezone.now() - timedelta(days=7),
        }

        score = calculate_subscriber_engagement(engagement_data)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_segment_subscribers(self):
        """Test subscriber segmentation."""
        subscribers = [
            {
                "email": "test1@example.com",
                "engagement_score": 0.8,
                "status": "subscribed",
            },
            {
                "email": "test2@example.com",
                "engagement_score": 0.3,
                "status": "subscribed",
            },
            {
                "email": "test3@example.com",
                "engagement_score": 0.9,
                "status": "subscribed",
            },
        ]

        segments = segment_subscribers(
            subscribers,
            {
                "high_engagement": {"engagement_score__gte": 0.7},
                "low_engagement": {"engagement_score__lt": 0.7},
            },
        )

        self.assertEqual(len(segments["high_engagement"]), 2)
        self.assertEqual(len(segments["low_engagement"]), 1)

    def test_validate_subscriber_data(self):
        """Test subscriber data validation."""
        valid_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "status": "subscribed",
        }

        result = validate_subscriber_data(valid_data)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_subscriber_data_invalid(self):
        """Test subscriber data validation with invalid data."""
        invalid_data = {
            "email": "invalid-email",
            "first_name": "",
            "last_name": "",
            "status": "invalid-status",
        }

        result = validate_subscriber_data(invalid_data)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 0)


class TestAnalyticsUtils(TestCase):
    """Test analytics utility functions."""

    def test_calculate_open_rate(self):
        """Test open rate calculation."""
        rate = calculate_open_rate(emails_delivered=100, emails_opened=20)
        self.assertEqual(rate, 20.0)

    def test_calculate_open_rate_zero_division(self):
        """Test open rate calculation with zero division."""
        rate = calculate_open_rate(emails_delivered=0, emails_opened=0)
        self.assertEqual(rate, 0.0)

    def test_calculate_click_rate(self):
        """Test click rate calculation."""
        rate = calculate_click_rate(emails_delivered=100, emails_clicked=5)
        self.assertEqual(rate, 5.0)

    def test_calculate_click_rate_zero_division(self):
        """Test click rate calculation with zero division."""
        rate = calculate_click_rate(emails_delivered=0, emails_clicked=0)
        self.assertEqual(rate, 0.0)

    def test_calculate_bounce_rate(self):
        """Test bounce rate calculation."""
        rate = calculate_bounce_rate(emails_sent=100, emails_bounced=3)
        self.assertEqual(rate, 3.0)

    def test_calculate_bounce_rate_zero_division(self):
        """Test bounce rate calculation with zero division."""
        rate = calculate_bounce_rate(emails_sent=0, emails_bounced=0)
        self.assertEqual(rate, 0.0)

    def test_generate_analytics_report(self):
        """Test analytics report generation."""
        data = {
            "campaigns": [
                {"name": "Campaign 1", "emails_sent": 100, "emails_opened": 20},
                {"name": "Campaign 2", "emails_sent": 200, "emails_opened": 40},
            ]
        }

        report = generate_analytics_report(data)
        self.assertIn("summary", report)
        self.assertIn("campaigns", report)
        self.assertIn("metrics", report)

    def test_process_email_events(self):
        """Test email events processing."""
        events = [
            {"event_type": "opened", "timestamp": timezone.now()},
            {"event_type": "clicked", "timestamp": timezone.now()},
            {"event_type": "bounced", "timestamp": timezone.now()},
        ]

        processed = process_email_events(events)
        self.assertIn("opens", processed)
        self.assertIn("clicks", processed)
        self.assertIn("bounces", processed)

    def test_calculate_engagement_score(self):
        """Test engagement score calculation."""
        metrics = {
            "opens": 10,
            "clicks": 5,
            "emails_sent": 20,
            "last_activity": timezone.now() - timedelta(days=7),
        }

        score = calculate_engagement_score(metrics)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_generate_dashboard_data(self):
        """Test dashboard data generation."""
        data = {"campaigns": [], "subscribers": [], "events": []}

        dashboard = generate_dashboard_data(data)
        self.assertIn("stats", dashboard)
        self.assertIn("charts", dashboard)
        self.assertIn("recent_activity", dashboard)


class TestAutomationUtils(TestCase):
    """Test automation utility functions."""

    def test_evaluate_workflow_conditions(self):
        """Test workflow conditions evaluation."""
        conditions = [
            {"field": "status", "operator": "equals", "value": "subscribed"},
            {"field": "engagement_score", "operator": "gte", "value": 0.5},
        ]

        subscriber_data = {"status": "subscribed", "engagement_score": 0.8}

        result = evaluate_workflow_conditions(conditions, subscriber_data)
        self.assertTrue(result)

    def test_evaluate_workflow_conditions_false(self):
        """Test workflow conditions evaluation with false result."""
        conditions = [
            {"field": "status", "operator": "equals", "value": "subscribed"},
            {"field": "engagement_score", "operator": "gte", "value": 0.9},
        ]

        subscriber_data = {"status": "subscribed", "engagement_score": 0.3}

        result = evaluate_workflow_conditions(conditions, subscriber_data)
        self.assertFalse(result)

    def test_execute_workflow_action(self):
        """Test workflow action execution."""
        action = {
            "type": "email",
            "config": {"template_id": 1, "subject": "Test Email"},
        }

        subscriber_data = {"email": "test@example.com", "first_name": "John"}

        result = execute_workflow_action(action, subscriber_data)
        self.assertTrue(result)

    def test_calculate_workflow_metrics(self):
        """Test workflow metrics calculation."""
        metrics_data = {
            "total_entries": 100,
            "completed_workflows": 75,
            "active_workflows": 25,
        }

        metrics = calculate_workflow_metrics(metrics_data)
        self.assertEqual(metrics["completion_rate"], 75.0)
        self.assertEqual(metrics["active_rate"], 25.0)

    def test_validate_workflow_config(self):
        """Test workflow configuration validation."""
        config = {
            "trigger_type": "subscriber_added",
            "trigger_config": {"list_id": 1},
            "entry_conditions": [],
            "exit_conditions": [],
        }

        result = validate_workflow_config(config)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_workflow_config_invalid(self):
        """Test workflow configuration validation with invalid config."""
        config = {
            "trigger_type": "invalid_trigger",
            "trigger_config": {},
            "entry_conditions": [],
            "exit_conditions": [],
        }

        result = validate_workflow_config(config)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_process_workflow_trigger(self):
        """Test workflow trigger processing."""
        trigger_data = {
            "type": "subscriber_added",
            "data": {"subscriber_id": 1, "list_id": 1},
        }

        result = process_workflow_trigger(trigger_data)
        self.assertTrue(result)

    def test_generate_workflow_report(self):
        """Test workflow report generation."""
        workflow_data = {
            "name": "Test Workflow",
            "total_entries": 100,
            "completed_workflows": 75,
        }

        report = generate_workflow_report(workflow_data)
        self.assertIn("workflow_name", report)
        self.assertIn("metrics", report)
        self.assertIn("summary", report)


class TestIntegrationUtils(TestCase):
    """Test integration utility functions."""

    def test_validate_webhook_signature_mailgun(self):
        """Test webhook signature validation for Mailgun."""
        with patch("apps.integrations.utils.hmac") as mock_hmac:
            mock_hmac.new.return_value.hexdigest.return_value = "test-signature"

            result = validate_webhook_signature(
                "mailgun",
                "test-timestamp",
                "test-token",
                "test-signature",
                "test-signing-key",
            )
            self.assertTrue(result)

    def test_validate_webhook_signature_invalid(self):
        """Test webhook signature validation with invalid signature."""
        result = validate_webhook_signature(
            "mailgun",
            "test-timestamp",
            "test-token",
            "invalid-signature",
            "test-signing-key",
        )
        self.assertFalse(result)

    def test_validate_webhook_signature_unsupported_provider(self):
        """Test webhook signature validation with unsupported provider."""
        result = validate_webhook_signature(
            "unsupported",
            "test-timestamp",
            "test-token",
            "test-signature",
            "test-signing-key",
        )
        self.assertFalse(result)

    def test_process_webhook_data(self):
        """Test webhook data processing."""
        webhook_data = {
            "event": "opened",
            "data": {
                "recipient": "test@example.com",
                "timestamp": timezone.now().isoformat(),
            },
        }

        result = process_webhook_data(webhook_data)
        self.assertTrue(result)

    def test_encrypt_credentials(self):
        """Test credentials encryption."""
        credentials = {"api_key": "test-key", "domain": "test.com"}
        encrypted = encrypt_credentials(credentials)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, json.dumps(credentials))

    def test_decrypt_credentials(self):
        """Test credentials decryption."""
        credentials = {"api_key": "test-key", "domain": "test.com"}
        encrypted = encrypt_credentials(credentials)
        decrypted = decrypt_credentials(encrypted)
        self.assertEqual(decrypted, credentials)

    def test_validate_integration_config(self):
        """Test integration configuration validation."""
        config = {
            "provider": "mailgun",
            "config": {"domain": "test.example.com"},
            "credentials": {"api_key": "test-key"},
        }

        result = validate_integration_config(config)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_integration_config_invalid(self):
        """Test integration configuration validation with invalid config."""
        config = {"provider": "invalid", "config": {}, "credentials": {}}

        result = validate_integration_config(config)
        self.assertFalse(result["is_valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_generate_webhook_url(self):
        """Test webhook URL generation."""
        url = generate_webhook_url("mailgun", "test-endpoint")
        self.assertIn("webhooks", url)
        self.assertIn("mailgun", url)
        self.assertIn("test-endpoint", url)


# Pytest-style tests for better integration
@pytest.mark.django_db
class TestUtilsIntegration:
    """Test utility functions integration with models."""

    def test_calculate_campaign_metrics_with_campaign(self, campaign):
        """Test campaign metrics calculation with campaign model."""
        campaign.emails_sent = 100
        campaign.emails_delivered = 95
        campaign.emails_opened = 20
        campaign.emails_clicked = 5
        campaign.save()

        metrics = calculate_campaign_metrics(
            campaign.emails_sent,
            campaign.emails_delivered,
            campaign.emails_opened,
            campaign.emails_clicked,
        )

        assert metrics["delivery_rate"] == 95.0
        assert metrics["open_rate"] == 21.05

    def test_calculate_subscriber_engagement_with_subscriber(self, subscriber):
        """Test subscriber engagement calculation with subscriber model."""
        engagement_data = {
            "emails_opened": 10,
            "emails_clicked": 5,
            "emails_sent": 20,
            "last_activity": timezone.now() - timedelta(days=7),
        }

        score = calculate_subscriber_engagement(engagement_data)
        assert 0.0 <= score <= 1.0

    def test_evaluate_workflow_conditions_with_workflow(
        self, automation_workflow, subscriber
    ):
        """Test workflow conditions evaluation with workflow model."""
        conditions = [
            {"field": "status", "operator": "equals", "value": "subscribed"},
            {"field": "engagement_score", "operator": "gte", "value": 0.5},
        ]

        subscriber_data = {"status": subscriber.status, "engagement_score": 0.8}

        result = evaluate_workflow_conditions(conditions, subscriber_data)
        assert result is True

    def test_process_webhook_data_with_models(self, subscriber, campaign):
        """Test webhook data processing with existing models."""
        webhook_data = {
            "event": "opened",
            "data": {
                "recipient": subscriber.email,
                "campaign_id": campaign.id,
                "timestamp": timezone.now().isoformat(),
            },
        }

        result = process_webhook_data(webhook_data)
        assert result is True


@pytest.mark.django_db
class TestUtilsErrorHandling:
    """Test utility functions error handling."""

    def test_calculate_campaign_metrics_invalid_data(self):
        """Test campaign metrics calculation with invalid data."""
        with pytest.raises(TypeError):
            calculate_campaign_metrics(
                emails_sent="invalid",
                emails_delivered=95,
                emails_opened=20,
                emails_clicked=5,
            )

    def test_validate_email_address_invalid_format(self):
        """Test email address validation with invalid format."""
        result = validate_email_address("not-an-email")
        assert result["is_valid"] is False
        assert "error" in result

    def test_process_subscriber_import_invalid_csv(self):
        """Test subscriber import processing with invalid CSV."""
        result = process_subscriber_import("invalid,csv,data")
        assert result["imported"] == 0
        assert result["errors"] > 0

    def test_evaluate_workflow_conditions_missing_field(self):
        """Test workflow conditions evaluation with missing field."""
        conditions = [
            {"field": "non_existent_field", "operator": "equals", "value": "test"}
        ]

        subscriber_data = {"status": "subscribed"}

        result = evaluate_workflow_conditions(conditions, subscriber_data)
        assert result is False

    def test_encrypt_credentials_invalid_data(self):
        """Test credentials encryption with invalid data."""
        with pytest.raises(TypeError):
            encrypt_credentials("invalid-data")

    def test_decrypt_credentials_invalid_data(self):
        """Test credentials decryption with invalid data."""
        result = decrypt_credentials("invalid-encrypted-data")
        assert result is None


@pytest.mark.django_db
class TestUtilsPerformance:
    """Test utility functions performance."""

    def test_process_subscriber_import_large_dataset(self):
        """Test subscriber import processing with large dataset."""
        # Generate large CSV data
        csv_data = "\n".join(
            [f"user{i}@example.com,User{i},Test,Company{i}" for i in range(1000)]
        )

        result = process_subscriber_import(csv_data, update_existing=True)
        assert result["imported"] == 1000
        assert result["errors"] == 0

    def test_calculate_engagement_score_performance(self):
        """Test engagement score calculation performance."""
        metrics = {
            "opens": 1000,
            "clicks": 500,
            "emails_sent": 2000,
            "last_activity": timezone.now() - timedelta(days=30),
        }

        score = calculate_engagement_score(metrics)
        assert 0.0 <= score <= 1.0

    def test_segment_subscribers_performance(self):
        """Test subscriber segmentation performance."""
        # Generate large subscriber dataset
        subscribers = [
            {
                "email": f"user{i}@example.com",
                "engagement_score": i / 1000,
                "status": "subscribed",
            }
            for i in range(1000)
        ]

        segments = segment_subscribers(
            subscribers,
            {
                "high_engagement": {"engagement_score__gte": 0.7},
                "medium_engagement": {
                    "engagement_score__gte": 0.4,
                    "engagement_score__lt": 0.7,
                },
                "low_engagement": {"engagement_score__lt": 0.4},
            },
        )

        assert len(segments["high_engagement"]) > 0
        assert len(segments["medium_engagement"]) > 0
        assert len(segments["low_engagement"]) > 0
