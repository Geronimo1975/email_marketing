from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging

from .models import EmailCampaign, CampaignRecipient
from .utils import validate_campaign_before_sending
from apps.integrations.services import MailgunService
from apps.subscribers.models import EmailContact
from apps.analytics.models import EmailEvent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_campaign_task(self, campaign_id):
    """
    Send a campaign to all recipients asynchronously.
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)

        # Validate campaign before sending
        validation_errors = validate_campaign_before_sending(campaign)
        if validation_errors:
            logger.error(
                f"Campaign {campaign_id} validation failed: {validation_errors}"
            )
            campaign.status = EmailCampaign.CampaignStatus.CANCELLED
            campaign.save()
            return {
                "status": "error",
                "message": "Validation failed",
                "errors": validation_errors,
            }

        # Update campaign status
        campaign.status = EmailCampaign.CampaignStatus.SENDING
        campaign.save()

        # Get all contacts from selected lists
        contacts = EmailContact.objects.filter(
            email_lists__in=campaign.email_lists.all(),
            is_subscribed=True,
            is_active=True,
        ).distinct()

        total_recipients = contacts.count()
        campaign.total_recipients = total_recipients
        campaign.save()

        if total_recipients == 0:
            logger.warning(f"No contacts found for campaign {campaign_id}")
            campaign.status = EmailCampaign.CampaignStatus.SENT
            campaign.save()
            return {"status": "warning", "message": "No contacts found"}

        # Initialize Mailgun service
        try:
            mailgun = MailgunService()
        except Exception as e:
            logger.error(f"Failed to initialize Mailgun service: {e}")
            campaign.status = EmailCampaign.CampaignStatus.CANCELLED
            campaign.save()
            return {"status": "error", "message": "Mailgun service unavailable"}

        return process_regular_campaign(campaign, list(contacts), mailgun)

    except EmailCampaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {"status": "error", "message": "Campaign not found"}
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {e}")
        campaign.status = EmailCampaign.CampaignStatus.CANCELLED
        campaign.save()
        raise self.retry(exc=e, countdown=60)


def process_regular_campaign(campaign, contacts, mailgun):
    """
    Process a regular campaign (no A/B testing).
    """
    sent_count = 0
    failed_count = 0

    # Create campaign recipients
    recipients = []
    for contact in contacts:
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            contact=contact,
            status=CampaignRecipient.RecipientStatus.PENDING,
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
                    "email": recipient.contact.email,
                    "vars": {
                        "first_name": recipient.contact.first_name or "",
                        "last_name": recipient.contact.last_name or "",
                        "email": recipient.contact.email,
                        "unsubscribe_url": (
                            f"{getattr(settings, 'SITE_URL', '')}/unsubscribe/"
                            f"{recipient.id}/"
                        ),
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
                recipient.status = CampaignRecipient.RecipientStatus.SENT
                recipient.sent_at = timezone.now()
                recipient.mailgun_message_id = response.get("id", "")
                recipient.save()
                sent_count += 1

            # Update campaign stats
            campaign.emails_sent += len(batch)
            campaign.save()

        except Exception as e:
            logger.error(
                f"Error sending batch {i}-{i + batch_size}: {e}"
            )
            for recipient in batch:
                recipient.status = CampaignRecipient.RecipientStatus.FAILED
                recipient.save()
                failed_count += 1

    # Update campaign status
    campaign.status = EmailCampaign.CampaignStatus.SENT
    campaign.sent_at = timezone.now()
    campaign.save()

    return {
        "status": "success",
        "message": "Campaign sent successfully",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_recipients": len(recipients),
    }


def process_ab_test_campaign(campaign, contacts, mailgun):
    """Minimal stub delegating to regular processing for compatibility with tests."""
    return process_regular_campaign(campaign, contacts, mailgun)


@shared_task
def process_scheduled_campaigns():
    """
    Process campaigns that are scheduled to be sent.
    """
    now = timezone.now()
    scheduled_campaigns = EmailCampaign.objects.filter(
        status=EmailCampaign.CampaignStatus.SCHEDULED, send_at__lte=now
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
        campaign = EmailCampaign.objects.get(id=campaign_id)

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

    except EmailCampaign.DoesNotExist:
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
    old_campaigns = EmailCampaign.objects.filter(
        status__in=[EmailCampaign.CampaignStatus.SENT, EmailCampaign.CampaignStatus.CANCELLED],
        created_at__lt=cutoff_date,
    )

    deleted_count = old_campaigns.count()
    old_campaigns.delete()

    return {"status": "success", "deleted_count": deleted_count}
