"""
Celery tasks for integrations.
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List

from .models import Integration, SyncJob, WebhookLog
from .services import MailgunService, OdooService
from apps.subscribers.models import Subscriber, SubscriberList

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_odoo_contacts(self, integration_id: int) -> Dict:
    """Sync contacts from Odoo to subscriber lists."""
    try:
        integration = Integration.objects.get(id=integration_id)

        # Create sync job
        sync_job = SyncJob.objects.create(
            integration=integration,
            job_type=SyncJob.JobType.ODOO_IMPORT_CONTACTS,
            status=SyncJob.Status.RUNNING,
            started_at=timezone.now(),
            created_by_id=1  # System user
        )

        try:
            # Initialize Odoo service
            credentials = integration.decrypt_credentials()
            odoo_service = OdooService(
                url=credentials.get('url'),
                username=credentials.get('username'),
                api_key=credentials.get('api_key'),
                database=credentials.get('database')
            )

            # Get contacts from Odoo
            contact_ids = odoo_service.search_contacts()
            sync_job.total_records = len(contact_ids)
            sync_job.save()

            # Process contacts in batches
            batch_size = 100
            for i in range(0, len(contact_ids), batch_size):
                batch_ids = contact_ids[i:i + batch_size]
                contacts = odoo_service.get_contacts(batch_ids)

                for contact in contacts:
                    try:
                        email = contact.get('email')
                        if not email:
                            continue

                        # Create or update subscriber
                        subscriber, created = Subscriber.objects.get_or_create(
                            email=email,
                            defaults={
                                'first_name': contact.get('name', '').split(' ')[0],
                                'last_name': ' '.join(contact.get('name', '').split(' ')[1:]),
                                'status': Subscriber.Status.SUBSCRIBED,
                                'odoo_contact_id': contact.get('id'),
                                'custom_fields': {
                                    'phone': contact.get('phone', ''),
                                    'mobile': contact.get('mobile', ''),
                                    'city': contact.get('city', ''),
                                    'country': contact.get('country_id', {}).get('name', '') if contact.get('country_id') else '',
                                    'is_company': contact.get('is_company', False)
                                }
                            }
                        )

                        if not created:
                            # Update existing subscriber
                            subscriber.odoo_contact_id = contact.get('id')
                            subscriber.first_name = contact.get('name', '').split(' ')[0]
                            subscriber.last_name = ' '.join(contact.get('name', '').split(' ')[1:])
                            subscriber.custom_fields.update({
                                'phone': contact.get('phone', ''),
                                'mobile': contact.get('mobile', ''),
                                'city': contact.get('city', ''),
                                'country': contact.get('country_id', {}).get('name', '') if contact.get('country_id') else '',
                                'is_company': contact.get('is_company', False)
                            })
                            subscriber.save()

                        sync_job.successful_records += 1

                    except Exception as e:
                        logger.error(f"Error processing contact {contact.get('id')}: {e}")
                        sync_job.failed_records += 1

                    sync_job.processed_records += 1

                sync_job.save()

            # Complete sync job
            sync_job.status = SyncJob.Status.COMPLETED
            sync_job.completed_at = timezone.now()
            sync_job.result_summary = {
                'total_processed': sync_job.processed_records,
                'successful': sync_job.successful_records,
                'failed': sync_job.failed_records
            }
            sync_job.save()

            # Update integration
            integration.last_sync = timezone.now()
            integration.save()

            return {
                'status': 'success',
                'processed': sync_job.processed_records,
                'successful': sync_job.successful_records,
                'failed': sync_job.failed_records
            }

        except Exception as e:
            sync_job.status = SyncJob.Status.FAILED
            sync_job.error_message = str(e)
            sync_job.completed_at = timezone.now()
            sync_job.save()

            integration.error_count += 1
            integration.last_error = str(e)
            integration.save()

            raise

    except Exception as e:
        logger.error(f"Sync job failed: {e}")
        raise self.retry(countdown=60 * (self.request.retries + 1))


@shared_task
def sync_mailgun_suppressions() -> Dict:
    """Sync Mailgun suppression lists with local subscriber status."""
    try:
        mailgun_service = MailgunService()

        # Sync bounces
        bounces = mailgun_service.get_suppressions('bounces')
        bounced_count = 0

        for bounce in bounces:
            email = bounce.get('address')
            if email:
                Subscriber.objects.filter(
                    email=email
                ).update(
                    status=Subscriber.Status.BOUNCED
                )
                bounced_count += 1

        # Sync unsubscribes
        unsubscribes = mailgun_service.get_suppressions('unsubscribes')
        unsubscribed_count = 0

        for unsubscribe in unsubscribes:
            email = unsubscribe.get('address')
            if email:
                Subscriber.objects.filter(
                    email=email
                ).update(
                    status=Subscriber.Status.UNSUBSCRIBED
                )
                unsubscribed_count += 1

        # Sync complaints
        complaints = mailgun_service.get_suppressions('complaints')
        complained_count = 0

        for complaint in complaints:
            email = complaint.get('address')
            if email:
                Subscriber.objects.filter(
                    email=email
                ).update(
                    status=Subscriber.Status.COMPLAINED
                )
                complained_count += 1

        return {
            'status': 'success',
            'bounced': bounced_count,
            'unsubscribed': unsubscribed_count,
            'complained': complained_count
        }

    except Exception as e:
        logger.error(f"Error syncing suppressions: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_webhook_logs(days: int = 30) -> Dict:
    """Clean up old webhook logs."""
    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = WebhookLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        return {
            'status': 'success',
            'deleted_logs': deleted_count
        }

    except Exception as e:
        logger.error(f"Error cleaning webhook logs: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def sync_subscriber_to_odoo(self, subscriber_id: int) -> Dict:
    """Sync individual subscriber data to Odoo."""
    try:
        subscriber = Subscriber.objects.get(id=subscriber_id)

        # Get Odoo integration for subscriber's team
        # (assuming subscriber belongs to first list's team)
        if not subscriber.lists.exists():
            return {'status': 'skipped', 'reason': 'No lists assigned'}

        team = subscriber.lists.first().team
        integration = Integration.objects.filter(
            team=team,
            provider=Integration.Provider.ODOO,
            status=Integration.Status.ACTIVE
        ).first()

        if not integration:
            return {'status': 'skipped', 'reason': 'No Odoo integration'}

        try:
            credentials = integration.decrypt_credentials()
            odoo_service = OdooService(
                url=credentials.get('url'),
                username=credentials.get('username'),
                api_key=credentials.get('api_key'),
                database=credentials.get('database')
            )

            # Prepare contact data
            contact_data = {
                'name': subscriber.full_name,
                'email': subscriber.email,
                'phone': subscriber.custom_fields.get('phone', ''),
                'mobile': subscriber.custom_fields.get('mobile', ''),
                'street': subscriber.custom_fields.get('street', ''),
                'city': subscriber.custom_fields.get('city', ''),
                'zip': subscriber.custom_fields.get('zip', ''),
            }

            if subscriber.odoo_contact_id:
                # Update existing contact
                success = odoo_service.update_contact(
                    subscriber.odoo_contact_id, contact_data
                )
                if success:
                    return {'status': 'updated', 'odoo_id': subscriber.odoo_contact_id}
                else:
                    return {'status': 'error', 'message': 'Update failed'}
            else:
                # Create new contact
                odoo_id = odoo_service.create_contact(contact_data)
                subscriber.odoo_contact_id = odoo_id
                subscriber.save()
                return {'status': 'created', 'odoo_id': odoo_id}

        except Exception as e:
            integration.error_count += 1
            integration.last_error = str(e)
            integration.save()
            raise

    except Exception as e:
        logger.error(f"Error syncing subscriber to Odoo: {e}")
        raise self.retry(countdown=60 * (self.request.retries + 1))


@shared_task
def export_engagement_to_odoo() -> Dict:
    """Export email engagement data to Odoo custom fields."""
    try:
        from apps.analytics.models import SubscriberActivity

        # Get all subscriber activities
        activities = SubscriberActivity.objects.select_related('subscriber').all()

        updated_count = 0
        error_count = 0

        for activity in activities:
            subscriber = activity.subscriber

            if not subscriber.odoo_contact_id:
                continue

            # Get Odoo integration for subscriber
            if not subscriber.lists.exists():
                continue

            team = subscriber.lists.first().team
            integration = Integration.objects.filter(
                team=team,
                provider=Integration.Provider.ODOO,
                status=Integration.Status.ACTIVE
            ).first()

            if not integration:
                continue

            try:
                credentials = integration.decrypt_credentials()
                odoo_service = OdooService(
                    url=credentials.get('url'),
                    username=credentials.get('username'),
                    api_key=credentials.get('api_key'),
                    database=credentials.get('database')
                )

                engagement_data = {
                    'engagement_score': activity.engagement_score,
                    'emails_opened': activity.emails_opened,
                    'emails_clicked': activity.emails_clicked,
                    'last_opened': activity.last_opened.isoformat() if activity.last_opened else None
                }

                odoo_service.sync_email_engagement(
                    subscriber.odoo_contact_id, engagement_data
                )
                updated_count += 1

            except Exception as e:
                logger.error(f"Error updating engagement for subscriber {subscriber.id}: {e}")
                error_count += 1

        return {
            'status': 'success',
            'updated': updated_count,
            'errors': error_count
        }

    except Exception as e:
        logger.error(f"Error exporting engagement data: {e}")
        return {'status': 'error', 'message': str(e)}