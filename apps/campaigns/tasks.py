from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

from .models import Campaign, CampaignRecipient, CampaignVariant
from .utils import validate_campaign_before_sending
from apps.integrations.services import MailgunService
from apps.subscribers.models import Subscriber
from apps.analytics.models import EmailEvent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_campaign_task(self, campaign_id):
    """
    Send a campaign to all recipients asynchronously.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)

        # Validate campaign before sending
        validation_errors = validate_campaign_before_sending(campaign)
        if validation_errors:
            logger.error(
                f"Campaign {campaign_id} validation failed: {validation_errors}"
            )
            campaign.status = Campaign.Status.CANCELLED
            campaign.save()
            return {
                "status": "error",
                "message": "Validation failed",
                "errors": validation_errors,
            }

        # Update campaign status
        campaign.status = Campaign.Status.SENDING
        campaign.save()

        # Get all subscribers from selected lists
        subscribers = Subscriber.objects.filter(
            lists__in=campaign.subscriber_lists.all(),
            status=Subscriber.Status.SUBSCRIBED,
        ).distinct()

        total_recipients = subscribers.count()
        campaign.total_recipients = total_recipients
        campaign.save()

        if total_recipients == 0:
            logger.warning(f"No subscribers found for campaign {campaign_id}")
            campaign.status = Campaign.Status.SENT
            campaign.save()
            return {"status": "warning", "message": "No subscribers found"}

        # Initialize Mailgun service
        try:
            mailgun = MailgunService()
        except Exception as e:
            logger.error(f"Failed to initialize Mailgun service: {e}")
            campaign.status = Campaign.Status.CANCELLED
            campaign.save()
            return {"status": "error", "message": "Mailgun service unavailable"}

        # Process A/B testing if enabled
        if campaign.type == Campaign.Type.AB_TEST and campaign.variants.exists():
            return process_ab_test_campaign(campaign, subscribers, mailgun)
        else:
            return process_regular_campaign(campaign, subscribers, mailgun)

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {"status": "error", "message": "Campaign not found"}
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {e}")
        campaign.status = Campaign.Status.CANCELLED
        campaign.save()
        raise self.retry(exc=e, countdown=60)


def process_regular_campaign(campaign, subscribers, mailgun):
    """
    Process a regular campaign (no A/B testing).
    """
    sent_count = 0
    failed_count = 0

    # Create campaign recipients
    recipients = []
    for subscriber in subscribers:
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            subscriber=subscriber,
            status=CampaignRecipient.Status.PENDING,
        )
        recipients.append(recipient)

    # Send emails in batches
    batch_size = 100
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i : i + batch_size]

        # Prepare recipient data for Mailgun
        recipient_data = []
        for recipient in batch:
            recipient_data.append(
                {
                    "email": recipient.subscriber.email,
                    "vars": {
                        "first_name": recipient.subscriber.first_name or "",
                        "last_name": recipient.subscriber.last_name or "",
                        "email": recipient.subscriber.email,
                        "unsubscribe_url": f"{settings.SITE_URL}/unsubscribe/{recipient.id}/",
                    },
                }
            )

        try:
            # Send batch via Mailgun
            response = mailgun.send_bulk_email(
                recipients=recipient_data,
                subject=campaign.subject,
                html_content=campaign.html_content,
                text_content=campaign.text_content,
                from_email=campaign.from_email,
                from_name=campaign.from_name,
                tags=[f"campaign-{campaign.id}"],
                track_opens=campaign.track_opens,
                track_clicks=campaign.track_clicks,
            )

            # Update recipient status
            for recipient in batch:
                recipient.status = CampaignRecipient.Status.SENT
                recipient.sent_at = timezone.now()
                recipient.mailgun_message_id = response.get("id", "")
                recipient.save()
                sent_count += 1

            # Update campaign stats
            campaign.emails_sent += len(batch)
            campaign.save()

        except Exception as e:
            logger.error(f"Error sending batch {i}-{i + batch_size}: {e}")
            for recipient in batch:
                recipient.status = CampaignRecipient.Status.FAILED
                recipient.save()
                failed_count += len(batch)

    # Update campaign status
    campaign.status = Campaign.Status.SENT
    campaign.sent_at = timezone.now()
    campaign.save()

    return {
        "status": "success",
        "message": f"Campaign sent successfully",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_recipients": len(recipients),
    }


def process_ab_test_campaign(campaign, subscribers, mailgun):
    """
    Process an A/B test campaign.
    """
    variants = list(campaign.variants.all())
    if not variants:
        return process_regular_campaign(campaign, subscribers, mailgun)

    # Calculate how many subscribers to send to each variant
    total_subscribers = len(subscribers)
    test_percentage = campaign.ab_test_percentage / 100
    test_subscribers_count = int(total_subscribers * test_percentage)

    # Split subscribers between variants
    test_subscribers = subscribers[:test_subscribers_count]
    remaining_subscribers = subscribers[test_subscribers_count:]

    # Send test emails
    test_results = {}
    for variant in variants:
        variant_subscribers = test_subscribers[: len(test_subscribers) // len(variants)]
        test_subscribers = test_subscribers[len(test_subscribers) // len(variants) :]

        result = send_variant_emails(campaign, variant, variant_subscribers, mailgun)
        test_results[variant.id] = result

    # Schedule winner email for remaining subscribers
    if remaining_subscribers:
        # For now, just send the original campaign to remaining subscribers
        # In a real implementation, you'd wait for test results and send the winner
        process_regular_campaign(campaign, remaining_subscribers, mailgun)

    return {
        "status": "success",
        "message": "A/B test campaign sent successfully",
        "test_results": test_results,
    }


def send_variant_emails(campaign, variant, subscribers, mailgun):
    """
    Send emails for a specific variant.
    """
    sent_count = 0
    failed_count = 0

    # Create campaign recipients for this variant
    recipients = []
    for subscriber in subscribers:
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            subscriber=subscriber,
            status=CampaignRecipient.Status.PENDING,
        )
        recipients.append(recipient)

    # Send emails
    for recipient in recipients:
        try:
            response = mailgun.send_email(
                to_email=recipient.subscriber.email,
                subject=variant.subject,
                html_content=variant.html_content,
                text_content=variant.text_content,
                from_email=campaign.from_email,
                from_name=campaign.from_name,
                tags=[f"campaign-{campaign.id}", f"variant-{variant.id}"],
                track_opens=campaign.track_opens,
                track_clicks=campaign.track_clicks,
            )

            recipient.status = CampaignRecipient.Status.SENT
            recipient.sent_at = timezone.now()
            recipient.mailgun_message_id = response.get("id", "")
            recipient.save()
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending variant email: {e}")
            recipient.status = CampaignRecipient.Status.FAILED
            recipient.save()
            failed_count += 1

    # Update variant stats
    variant.emails_sent = sent_count
    variant.save()

    return {"sent_count": sent_count, "failed_count": failed_count}


@shared_task
def process_scheduled_campaigns():
    """
    Process campaigns that are scheduled to be sent.
    """
    now = timezone.now()
    scheduled_campaigns = Campaign.objects.filter(
        status=Campaign.Status.SCHEDULED, send_at__lte=now
    )

    processed_count = 0
    for campaign in scheduled_campaigns:
        try:
            send_campaign_task.delay(campaign.id)
            processed_count += 1
        except Exception as e:
            logger.error(f"Error scheduling campaign {campaign.id}: {e}")

    return {
        "status": "success",
        "processed_count": processed_count,
        "total_scheduled": scheduled_campaigns.count(),
    }


@shared_task
def update_campaign_stats(campaign_id):
    """
    Update campaign statistics based on email events.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)

        # Get email events for this campaign
        events = EmailEvent.objects.filter(campaign=campaign)

        # Update basic stats
        campaign.emails_delivered = events.filter(
            event_type=EmailEvent.EventType.DELIVERED
        ).count()

        campaign.emails_bounced = events.filter(
            event_type=EmailEvent.EventType.BOUNCED
        ).count()

        campaign.emails_opened = (
            events.filter(event_type=EmailEvent.EventType.OPENED)
            .distinct("recipient_email")
            .count()
        )

        campaign.emails_clicked = (
            events.filter(event_type=EmailEvent.EventType.CLICKED)
            .distinct("recipient_email")
            .count()
        )

        campaign.unsubscribes = events.filter(
            event_type=EmailEvent.EventType.UNSUBSCRIBED
        ).count()

        campaign.complaints = events.filter(
            event_type=EmailEvent.EventType.COMPLAINED
        ).count()

        campaign.save()

        return {
            "status": "success",
            "message": f"Updated stats for campaign {campaign_id}",
        }

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {"status": "error", "message": "Campaign not found"}
    except Exception as e:
        logger.error(f"Error updating campaign stats {campaign_id}: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def cleanup_old_campaigns():
    """
    Clean up old completed campaigns and their data.
    """
    from datetime import timedelta

    # Delete campaigns older than 1 year
    cutoff_date = timezone.now() - timedelta(days=365)
    old_campaigns = Campaign.objects.filter(
        status__in=[Campaign.Status.SENT, Campaign.Status.CANCELLED],
        created_at__lt=cutoff_date,
    )

    deleted_count = old_campaigns.count()
    old_campaigns.delete()

    return {"status": "success", "deleted_count": deleted_count}
