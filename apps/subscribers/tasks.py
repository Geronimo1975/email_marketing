from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

from .models import Subscriber, SubscriberList, Tag
from .utils import (
    process_subscriber_import,
    export_subscribers_to_csv,
    sync_subscribers_with_odoo,
    calculate_engagement_score,
)
from apps.integrations.services import OdooService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def import_subscribers_task(self, list_id, file_content, user_id):
    """
    Import subscribers from CSV/Excel file asynchronously.
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)
        subscriber_list = SubscriberList.objects.get(id=list_id)

        # Process the import
        results = process_subscriber_import(
            file_content, list_id, update_existing=True, skip_duplicates=True
        )

        # Log results
        logger.info(
            f"Import completed for list {list_id}: "
            f"{results['imported']} imported, "
            f"{results['updated']} updated, "
            f"{results['skipped']} skipped, "
            f"{len(results['errors'])} errors"
        )

        return {
            "status": "success",
            "message": "Import completed successfully",
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error importing subscribers: {e}")
        return {
            "status": "error",
            "message": "Failed to import subscribers",
            "error": str(e),
        }


@shared_task(bind=True, max_retries=3)
def export_subscribers_task(self, list_id, user_id, format="csv"):
    """
    Export subscribers to CSV/Excel file asynchronously.
    """
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)
        subscriber_list = SubscriberList.objects.get(id=list_id)

        # Generate export data
        if format == "csv":
            file_content = export_subscribers_to_csv(list_id)
            file_extension = "csv"
        else:
            # For Excel export, you would use openpyxl or xlsxwriter
            file_content = export_subscribers_to_csv(list_id)
            file_extension = "csv"

        # In a real implementation, you would save the file and send it via email
        # or provide a download link
        logger.info(f"Export completed for list {list_id}")

        return {
            "status": "success",
            "message": "Export completed successfully",
            "file_content": file_content,
            "file_extension": file_extension,
        }

    except Exception as e:
        logger.error(f"Error exporting subscribers: {e}")
        return {
            "status": "error",
            "message": "Failed to export subscribers",
            "error": str(e),
        }


@shared_task
def sync_subscribers_task():
    """
    Sync subscribers with external systems (Odoo, etc.).
    """
    try:
        # Sync with Odoo
        odoo_results = sync_subscribers_with_odoo()

        return {
            "status": "success",
            "message": "Sync completed successfully",
            "odoo_synced": odoo_results.get("synced_count", 0),
        }

    except Exception as e:
        logger.error(f"Error syncing subscribers: {e}")
        return {
            "status": "error",
            "message": "Failed to sync subscribers",
            "error": str(e),
        }


@shared_task
def update_engagement_scores():
    """
    Update engagement scores for all subscribers.
    """
    try:
        subscribers = Subscriber.objects.filter(status=Subscriber.Status.SUBSCRIBED)

        updated_count = 0
        for subscriber in subscribers:
            try:
                calculate_engagement_score(subscriber)
                updated_count += 1
            except Exception as e:
                logger.error(
                    f"Error updating engagement score for subscriber {subscriber.id}: {e}"
                )

        return {
            "status": "success",
            "message": f"Updated engagement scores for {updated_count} subscribers",
            "updated_count": updated_count,
        }

    except Exception as e:
        logger.error(f"Error updating engagement scores: {e}")
        return {
            "status": "error",
            "message": "Failed to update engagement scores",
            "error": str(e),
        }


@shared_task
def cleanup_inactive_subscribers():
    """
    Clean up inactive subscribers and their data.
    """
    from datetime import timedelta

    try:
        # Delete subscribers who have been unsubscribed for more than 1 year
        cutoff_date = timezone.now() - timedelta(days=365)
        old_unsubscribed = Subscriber.objects.filter(
            status=Subscriber.Status.UNSUBSCRIBED,
            updated_at__lt=cutoff_date,
        )

        deleted_count = old_unsubscribed.count()
        old_unsubscribed.delete()

        # Delete bounced subscribers who have been bounced for more than 6 months
        bounce_cutoff = timezone.now() - timedelta(days=180)
        old_bounced = Subscriber.objects.filter(
            status=Subscriber.Status.BOUNCED,
            updated_at__lt=bounce_cutoff,
        )

        bounced_deleted_count = old_bounced.count()
        old_bounced.delete()

        return {
            "status": "success",
            "message": "Cleanup completed successfully",
            "unsubscribed_deleted": deleted_count,
            "bounced_deleted": bounced_deleted_count,
        }

    except Exception as e:
        logger.error(f"Error cleaning up inactive subscribers: {e}")
        return {
            "status": "error",
            "message": "Failed to cleanup inactive subscribers",
            "error": str(e),
        }


@shared_task
def process_subscriber_activity():
    """
    Process subscriber activity data and update metrics.
    """
    try:
        from apps.analytics.models import EmailEvent, SubscriberActivity
        from django.db.models import Count

        # Get all subscribers
        subscribers = Subscriber.objects.all()

        processed_count = 0
        for subscriber in subscribers:
            try:
                # Get activity data for the last 30 days
                end_date = timezone.now()
                start_date = end_date - timedelta(days=30)

                # Count opens
                opens = EmailEvent.objects.filter(
                    recipient_email=subscriber.email,
                    event_type=EmailEvent.EventType.OPENED,
                    timestamp__gte=start_date,
                ).count()

                # Count clicks
                clicks = EmailEvent.objects.filter(
                    recipient_email=subscriber.email,
                    event_type=EmailEvent.EventType.CLICKED,
                    timestamp__gte=start_date,
                ).count()

                # Update or create activity record
                activity, created = SubscriberActivity.objects.get_or_create(
                    subscriber=subscriber,
                    date=timezone.now().date(),
                    defaults={"opens": opens, "clicks": clicks},
                )

                if not created:
                    activity.opens = opens
                    activity.clicks = clicks
                    activity.save()

                processed_count += 1

            except Exception as e:
                logger.error(
                    f"Error processing activity for subscriber {subscriber.id}: {e}"
                )

        return {
            "status": "success",
            "message": f"Processed activity for {processed_count} subscribers",
            "processed_count": processed_count,
        }

    except Exception as e:
        logger.error(f"Error processing subscriber activity: {e}")
        return {
            "status": "error",
            "message": "Failed to process subscriber activity",
            "error": str(e),
        }


@shared_task
def send_welcome_emails():
    """
    Send welcome emails to new subscribers.
    """
    try:
        from apps.campaigns.models import Campaign
        from apps.campaigns.tasks import send_campaign_task

        # Find campaigns with welcome email trigger
        welcome_campaigns = Campaign.objects.filter(
            type=Campaign.Type.WELCOME,
            status=Campaign.Status.ACTIVE,
        )

        sent_count = 0
        for campaign in welcome_campaigns:
            try:
                # Get new subscribers who haven't received welcome email
                new_subscribers = campaign.subscriber_lists.filter(
                    subscribers__created_at__gte=timezone.now() - timedelta(hours=1),
                    subscribers__welcome_email_sent=False,
                )

                if new_subscribers.exists():
                    # Send campaign
                    result = send_campaign_task.delay(campaign.id)
                    sent_count += 1

            except Exception as e:
                logger.error(
                    f"Error sending welcome email for campaign {campaign.id}: {e}"
                )

        return {
            "status": "success",
            "message": f"Sent {sent_count} welcome emails",
            "sent_count": sent_count,
        }

    except Exception as e:
        logger.error(f"Error sending welcome emails: {e}")
        return {
            "status": "error",
            "message": "Failed to send welcome emails",
            "error": str(e),
        }


@shared_task
def update_subscriber_segments():
    """
    Update subscriber segments based on rules.
    """
    try:
        from .models import SegmentRule

        # Get all active segment rules
        rules = SegmentRule.objects.filter(is_active=True)

        updated_count = 0
        for rule in rules:
            try:
                # Apply rule to segment subscribers
                from .utils import segment_subscribers

                subscribers = segment_subscribers(rule)

                # Update segment membership
                # This would depend on your segment implementation
                updated_count += subscribers.count()

            except Exception as e:
                logger.error(f"Error updating segment for rule {rule.id}: {e}")

        return {
            "status": "success",
            "message": f"Updated {updated_count} subscriber segments",
            "updated_count": updated_count,
        }

    except Exception as e:
        logger.error(f"Error updating subscriber segments: {e}")
        return {
            "status": "error",
            "message": "Failed to update subscriber segments",
            "error": str(e),
        }
