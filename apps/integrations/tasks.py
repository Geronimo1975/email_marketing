"""
Celery tasks for integrations.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from typing import Dict, List

from .models import Integration, SyncJob, WebhookLog
from .services import MailgunService, OdooService
from apps.subscribers.models import EmailContact, EmailList
from apps.analytics.models import EmailEvent, ContactActivity

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_odoo_contacts_task(self, integration_id: int) -> Dict:
    """Sync contacts from Odoo to email contacts."""
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
            contact_ids = odoo_service.search_contacts(limit=500)
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

                        name = contact.get('name', '')
                        name_parts = name.split(' ') if name else []

                        # Create or update email contact
                        contact_obj, created = EmailContact.objects.get_or_create(
                            email=email,
                            defaults={
                                'first_name': name_parts[0] if name_parts else '',
                                'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                                'phone': contact.get('phone') or contact.get('mobile', ''),
                                'company_name': name if contact.get('is_company') else '',
                                'street_address': contact.get('street', ''),
                                'city': contact.get('city', ''),
                                'postal_code': contact.get('zip', ''),
                                'country': contact.get('country_id', [None, ''])[1] if contact.get('country_id') else '',
                                'source': EmailContact.ContactSource.ODOO_IMPORT,
                                'odoo_id': contact.get('id'),
                                'gdpr_consent': True,  # Assume consent from CRM
                                'is_subscribed': True,
                                'tags': contact.get('category_id', []),
                            }
                        )

                        if not created:
                            # Update existing contact
                            contact_obj.first_name = name_parts[0] if name_parts else contact_obj.first_name
                            contact_obj.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else contact_obj.last_name
                            contact_obj.phone = contact.get('phone') or contact.get('mobile') or contact_obj.phone
                            contact_obj.street_address = contact.get('street', '') or contact_obj.street_address
                            contact_obj.city = contact.get('city', '') or contact_obj.city
                            contact_obj.postal_code = contact.get('zip', '') or contact_obj.postal_code
                            contact_obj.country = (contact.get('country_id', [None, ''])[1] if contact.get('country_id') else '') or contact_obj.country
                            contact_obj.odoo_id = contact.get('id')
                            contact_obj.save()

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
def update_suppression_lists_task() -> Dict:
    """Sync Mailgun suppression lists with local contact status."""
    try:
        mailgun_service = MailgunService()

        # Sync bounces
        bounces = mailgun_service.get_suppressions('bounces')
        bounced_count = 0

        for bounce in bounces:
            email = bounce.get('address')
            if email:
                EmailContact.objects.filter(email=email).update(
                    is_bounced=True,
                    bounce_count=1
                )
                bounced_count += 1

        # Sync unsubscribes
        unsubscribes = mailgun_service.get_suppressions('unsubscribes')
        unsubscribed_count = 0

        for unsubscribe in unsubscribes:
            email = unsubscribe.get('address')
            if email:
                EmailContact.objects.filter(email=email).update(
                    is_subscribed=False,
                    unsubscribed_at=timezone.now()
                )
                unsubscribed_count += 1

        # Sync complaints
        complaints = mailgun_service.get_suppressions('complaints')
        complained_count = 0

        for complaint in complaints:
            email = complaint.get('address')
            if email:
                EmailContact.objects.filter(email=email).update(
                    is_subscribed=False,
                    complained_at=timezone.now()
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
def cleanup_old_webhook_logs_task(days: int = 30) -> Dict:
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
def sync_subscriber_to_odoo(self, contact_id: int) -> Dict:
    """Sync individual email contact data to Odoo."""
    try:
        contact = EmailContact.objects.get(id=contact_id)

        # Get Odoo integration
        integration = Integration.objects.filter(
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
                'name': f"{contact.first_name} {contact.last_name}".strip() or contact.company_name,
                'email': contact.email,
                'phone': contact.phone,
                'street': contact.street_address,
                'city': contact.city,
                'zip': contact.postal_code,
                'is_company': bool(contact.company_name and not contact.first_name)
            }

            if contact.odoo_id:
                # Update existing contact
                success = odoo_service.update_contact(
                    contact.odoo_id, contact_data
                )
                if success:
                    return {'status': 'updated', 'odoo_id': contact.odoo_id}
                else:
                    return {'status': 'error', 'message': 'Update failed'}
            else:
                # Create new contact
                odoo_id = odoo_service.create_contact(contact_data)
                contact.odoo_id = odoo_id
                contact.save()
                return {'status': 'created', 'odoo_id': odoo_id}

        except Exception as e:
            integration.error_count += 1
            integration.last_error = str(e)
            integration.save()
            raise

    except Exception as e:
        logger.error(f"Error syncing contact to Odoo: {e}")
        raise self.retry(countdown=60 * (self.request.retries + 1))


@shared_task
def export_engagement_to_odoo_task() -> Dict:
    """Export email engagement data to Odoo custom fields."""
    try:
        # Get contacts with Odoo IDs and recent activity
        thirty_days_ago = timezone.now() - timedelta(days=30)
        contacts = EmailContact.objects.filter(
            odoo_id__isnull=False,
            last_email_activity__gte=thirty_days_ago
        )

        # Get Odoo integration
        integration = Integration.objects.filter(
            provider=Integration.Provider.ODOO,
            status=Integration.Status.ACTIVE
        ).first()

        if not integration:
            return {'status': 'skipped', 'reason': 'No Odoo integration'}

        credentials = integration.decrypt_credentials()
        odoo_service = OdooService(
            url=credentials.get('url'),
            username=credentials.get('username'),
            api_key=credentials.get('api_key'),
            database=credentials.get('database')
        )

        updated_count = 0
        error_count = 0

        for contact in contacts:
            try:
                # Calculate engagement metrics
                recent_events = EmailEvent.objects.filter(
                    recipient__contact=contact,
                    timestamp__gte=thirty_days_ago
                )

                engagement_data = {
                    'engagement_score': contact.engagement_score,
                    'emails_opened': recent_events.filter(event_type=EmailEvent.EventType.OPENED).count(),
                    'emails_clicked': recent_events.filter(event_type=EmailEvent.EventType.CLICKED).count(),
                    'last_opened': contact.last_engagement.isoformat() if contact.last_engagement else None,
                }

                odoo_service.sync_email_engagement(
                    contact.odoo_id, engagement_data
                )
                updated_count += 1

            except Exception as e:
                logger.error(f"Error updating engagement for contact {contact.id}: {e}")
                error_count += 1

        return {
            'status': 'success',
            'updated': updated_count,
            'errors': error_count
        }

    except Exception as e:
        logger.error(f"Error exporting engagement data: {e}")
        return {'status': 'error', 'message': str(e)}

# Backwards-compatibility wrappers expected by tests
@shared_task(bind=True, max_retries=3)
def sync_odoo_contacts(self, integration_id: int) -> Dict:
    return sync_odoo_contacts_task(self, integration_id)

@shared_task
def sync_mailgun_suppressions() -> Dict:
    return update_suppression_lists_task()

@shared_task
def cleanup_old_webhook_logs(days: int = 30) -> Dict:
    return cleanup_old_webhook_logs_task(days)