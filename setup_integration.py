#!/usr/bin/env python
"""
Setup Odoo integration with proper team structure
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.integrations.models import Integration, SyncJob
from apps.accounts.models import Team, User
from apps.subscribers.models import EmailContact
from django.conf import settings


def setup_team_and_integration():
    """Set up team and Odoo integration."""
    print("🏢 Setting up North Cleaning Services Team...")

    # Get or create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@north-cleaning.de',
            'first_name': 'Admin',
            'last_name': 'User',
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

    # Create team
    team, created = Team.objects.get_or_create(
        name='North Cleaning Services',
        defaults={
            'slug': 'north-cleaning',
            'description': 'North Cleaning Services Hamburg - Email Marketing Team',
            'is_active': True
        }
    )

    if created:
        print(f"✅ Created team: {team.name}")
    else:
        print(f"✅ Using existing team: {team.name}")

    # Add admin to team
    from apps.accounts.models import TeamMembership
    membership, created = TeamMembership.objects.get_or_create(
        team=team,
        user=admin_user,
        defaults={
            'role': TeamMembership.Role.ADMIN,
            'is_active': True
        }
    )

    if created:
        print(f"✅ Added {admin_user.username} to team as admin")

    # Create Odoo integration
    integration, created = Integration.objects.get_or_create(
        provider=Integration.Provider.ODOO,
        team=team,
        defaults={
            'name': 'North Cleaning Services - Odoo CRM',
            'status': Integration.Status.ACTIVE,
            'created_by': admin_user,
            'config': {
                'sync_frequency': 'daily',
                'import_all_contacts': True,
                'auto_sync_enabled': True
            }
        }
    )

    if created:
        print(f"✅ Created Odoo integration: {integration.name}")
    else:
        print(f"✅ Using existing integration: {integration.name}")

    # Store credentials
    integration.encrypt_credentials({
        'url': settings.ODOO_URL,
        'username': settings.ODOO_USERNAME,
        'api_key': settings.ODOO_API_KEY,
        'database': settings.ODOO_DATABASE
    })
    integration.save()

    print(f"🔑 Stored Odoo credentials")
    print(f"   URL: {settings.ODOO_URL}")
    print(f"   Database: {settings.ODOO_DATABASE}")
    print(f"   Username: {settings.ODOO_USERNAME}")

    return team, integration


def test_odoo_sync(integration):
    """Test the Odoo synchronization."""
    print(f"\n🔄 Testing Odoo Contact Sync...")

    try:
        from apps.integrations.services import OdooService

        # Test direct connection
        odoo_service = OdooService()
        print("✅ OdooService initialized")

        # Test authentication
        uid = odoo_service._authenticate()
        print(f"✅ Authentication successful (UID: {uid})")

        # Get contacts
        contact_ids = odoo_service.search_contacts(
            domain=[['email', '!=', False]],
            limit=5
        )
        print(f"✅ Found {len(contact_ids)} contacts in Odoo")

        if contact_ids:
            contacts = odoo_service.get_contacts(contact_ids)
            print(f"✅ Retrieved {len(contacts)} contact details")

            # Import contacts manually (simplified)
            imported_count = 0
            for contact_data in contacts:
                email = contact_data.get('email')
                if not email:
                    continue

                name = contact_data.get('name', '')
                name_parts = name.split(' ') if name else []

                contact_obj, created = EmailContact.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': name_parts[0] if name_parts else '',
                        'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                        'company_name': name if contact_data.get('is_company') else '',
                        'phone': contact_data.get('phone') or contact_data.get('mobile', ''),
                        'source': EmailContact.ContactSource.ODOO_IMPORT,
                        'odoo_id': contact_data.get('id'),
                        'gdpr_consent': True,
                        'is_subscribed': True,
                    }
                )

                if created:
                    imported_count += 1
                    print(f"   ✅ Imported: {contact_obj.email}")

            print(f"📊 Successfully imported {imported_count} new contacts")

            # Show total contacts
            total_contacts = EmailContact.objects.count()
            print(f"📈 Total contacts in database: {total_contacts}")

            return True

    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        return False


def show_admin_access():
    """Show admin access information."""
    print("\n🎛️  Django Admin Access:")
    print("=" * 40)
    print("🌐 URL: http://localhost:8000/admin/")
    print("👤 Username: admin")
    print("🔑 Password: admin123")
    print()
    print("📋 Available Sections:")
    print("   📧 Email Contacts - View imported contacts")
    print("   📝 Email Lists - Organize contacts")
    print("   🚀 Email Campaigns - Create campaigns")
    print("   🔗 Integrations - Manage Odoo connection")
    print("   📊 Analytics - View performance metrics")


def main():
    """Main setup function."""
    print("🚀 North Cleaning Services - Odoo Integration Setup")
    print("=" * 60)

    try:
        # Setup team and integration
        team, integration = setup_team_and_integration()

        # Test the sync
        sync_success = test_odoo_sync(integration)

        if sync_success:
            print("\n🎉 Odoo integration setup completed successfully!")
            show_admin_access()
        else:
            print("\n⚠️  Integration setup completed, but sync test failed")
            print("Check the error messages above for details")

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()