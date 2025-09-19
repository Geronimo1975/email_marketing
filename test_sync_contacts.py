#!/usr/bin/env python
"""
Test the Odoo contact sync functionality through Django models
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.integrations.models import Integration, SyncJob
from apps.integrations.tasks import sync_odoo_contacts_task
from apps.subscribers.models import EmailContact
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


def test_integration_setup():
    """Test setting up the Odoo integration in Django."""
    print("🔧 Setting up Odoo Integration in Django...")

    # Get or create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@north-cleaning.de',
            'is_staff': True,
            'is_superuser': True
        }
    )

    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✅ Created admin user: {admin_user.username}")
    else:
        print(f"✅ Using existing admin user: {admin_user.username}")

    # Create or update Odoo integration
    integration, created = Integration.objects.get_or_create(
        provider=Integration.Provider.ODOO,
        defaults={
            'name': 'North Cleaning Services - Odoo CRM',
            'status': Integration.Status.ACTIVE,
            'team_id': 1,  # Default team
            'created_by': admin_user,
            'config': {
                'sync_frequency': 'daily',
                'import_all_contacts': True,
                'last_sync_date': None
            }
        }
    )

    if created:
        print(f"✅ Created new integration: {integration.name}")
    else:
        print(f"✅ Using existing integration: {integration.name}")

    # Store Odoo credentials
    integration.encrypt_credentials({
        'url': settings.ODOO_URL,
        'username': settings.ODOO_USERNAME,
        'api_key': settings.ODOO_API_KEY,
        'database': settings.ODOO_DATABASE
    })
    integration.save()

    print(f"🔑 Stored Odoo credentials for: {settings.ODOO_URL}")

    return integration


def test_contact_sync(integration):
    """Test syncing contacts from Odoo."""
    print("\n📥 Testing Contact Sync from Odoo...")

    # Count existing contacts
    existing_count = EmailContact.objects.count()
    print(f"📊 Existing contacts in database: {existing_count}")

    try:
        # Run sync task
        print("🔄 Starting Odoo contact sync...")
        result = sync_odoo_contacts_task(integration.id)

        print(f"✅ Sync completed successfully!")
        print(f"📊 Sync results: {result}")

        # Count new contacts
        new_count = EmailContact.objects.count()
        imported_count = new_count - existing_count

        print(f"📈 New contacts imported: {imported_count}")
        print(f"📊 Total contacts now: {new_count}")

        # Show sample contacts
        if imported_count > 0:
            print("\n👥 Sample imported contacts:")
            recent_contacts = EmailContact.objects.filter(
                source=EmailContact.ContactSource.ODOO_IMPORT
            ).order_by('-created_at')[:3]

            for i, contact in enumerate(recent_contacts, 1):
                print(f"   {i}. {contact.first_name} {contact.last_name}")
                print(f"      Email: {contact.email}")
                print(f"      Company: {contact.company_name}")
                print(f"      Phone: {contact.phone}")
                print(f"      Odoo ID: {contact.odoo_id}")
                print()

        return True

    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False


def test_sync_job_status(integration):
    """Check sync job status."""
    print("📋 Checking Sync Job Status...")

    recent_jobs = SyncJob.objects.filter(
        integration=integration,
        job_type=SyncJob.JobType.ODOO_IMPORT_CONTACTS
    ).order_by('-created_at')[:3]

    if recent_jobs:
        print(f"📈 Found {recent_jobs.count()} recent sync jobs:")

        for i, job in enumerate(recent_jobs, 1):
            print(f"\n   Job {i}:")
            print(f"   ├─ Status: {job.get_status_display()}")
            print(f"   ├─ Started: {job.started_at}")
            print(f"   ├─ Completed: {job.completed_at}")
            print(f"   ├─ Total Records: {job.total_records}")
            print(f"   ├─ Successful: {job.successful_records}")
            print(f"   ├─ Failed: {job.failed_records}")
            print(f"   └─ Progress: {job.progress_percentage:.1f}%")

    else:
        print("ℹ️  No sync jobs found")


def main():
    """Main test function."""
    print("🚀 Testing North Cleaning Services - Odoo Integration")
    print("=" * 60)

    # Test integration setup
    integration = test_integration_setup()

    # Test contact sync
    sync_success = test_contact_sync(integration)

    # Check job status
    test_sync_job_status(integration)

    if sync_success:
        print("\n🎉 Odoo integration test completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Access Django admin: http://localhost:8000/admin/")
        print("   2. View 'Email Contacts' to see imported contacts")
        print("   3. Check 'Integrations > Sync Jobs' for job history")
        print("   4. Set up automated sync schedules")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")


if __name__ == "__main__":
    main()