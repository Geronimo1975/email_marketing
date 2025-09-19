#!/usr/bin/env python
"""
Test script for Odoo integration
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.integrations.services import OdooService
from django.conf import settings


def test_odoo_connection():
    """Test basic Odoo connectivity and authentication."""
    print("🔌 Testing Odoo Integration for North Cleaning Services")
    print("=" * 60)

    try:
        # Initialize Odoo service
        print(f"📍 Odoo URL: {settings.ODOO_URL}")
        print(f"👤 Username: {settings.ODOO_USERNAME}")
        print(f"🔑 API Key: {'*' * (len(settings.ODOO_API_KEY) - 8) + settings.ODOO_API_KEY[-8:]}")
        print()

        odoo_service = OdooService()
        print("✅ OdooService initialized successfully")

        # Test authentication
        print("🔐 Testing authentication...")
        uid = odoo_service._authenticate()

        if uid:
            print(f"✅ Authentication successful! User ID: {uid}")
        else:
            print("❌ Authentication failed")
            return False

        print()

        # Test contact search
        print("👥 Testing contact search...")
        try:
            # Search for contacts (limit to 5 for testing)
            contact_ids = odoo_service.search_contacts(limit=5)
            print(f"✅ Found {len(contact_ids)} contacts")

            if contact_ids:
                # Get contact details
                print("📋 Fetching contact details...")
                contacts = odoo_service.get_contacts(contact_ids[:3])  # Get first 3

                print(f"✅ Retrieved {len(contacts)} contact records")

                for i, contact in enumerate(contacts, 1):
                    print(f"\n📧 Contact {i}:")
                    print(f"   Name: {contact.get('name', 'N/A')}")
                    print(f"   Email: {contact.get('email', 'N/A')}")
                    print(f"   Phone: {contact.get('phone', 'N/A')}")
                    print(f"   City: {contact.get('city', 'N/A')}")
                    print(f"   Is Company: {contact.get('is_company', False)}")

            else:
                print("ℹ️  No contacts found (this might be normal for a new system)")

        except Exception as e:
            print(f"⚠️  Contact search failed: {e}")

        print()

        # Test creating a test contact
        print("➕ Testing contact creation...")
        try:
            test_contact_data = {
                'name': 'Test Hamburg Business',
                'email': 'test.hamburg@example.com',
                'phone': '+49 40 123456789',
                'street': 'Musterstraße 123',
                'city': 'Hamburg',
                'zip': '20095',
                'country_id': 57,  # Germany country ID (might vary)
                'is_company': True,
                'comment': 'Test contact created by email marketing integration'
            }

            contact_id = odoo_service.create_contact(test_contact_data)

            if contact_id:
                print(f"✅ Test contact created successfully! ID: {contact_id}")

                # Try to update the contact
                print("📝 Testing contact update...")
                update_data = {
                    'mobile': '+49 40 987654321',
                    'comment': 'Updated by email marketing integration test'
                }

                success = odoo_service.update_contact(contact_id, update_data)
                if success:
                    print("✅ Contact update successful")
                else:
                    print("⚠️  Contact update failed")

            else:
                print("⚠️  Contact creation returned no ID")

        except Exception as e:
            print(f"⚠️  Contact creation failed: {e}")

        print()

        # Test email search
        print("🔍 Testing email search...")
        try:
            test_email = settings.ODOO_USERNAME  # Use the configured email
            found_contact = odoo_service.get_contact_by_email(test_email)

            if found_contact:
                print(f"✅ Found contact by email: {found_contact.get('name')}")
            else:
                print(f"ℹ️  No contact found with email: {test_email}")

        except Exception as e:
            print(f"⚠️  Email search failed: {e}")

        print()
        print("🎉 Odoo integration test completed!")
        return True

    except Exception as e:
        print(f"❌ Odoo integration test failed: {e}")
        return False


def test_sync_task():
    """Test the Odoo sync Celery task."""
    print("\n🔄 Testing Odoo Sync Task")
    print("=" * 30)

    try:
        from apps.integrations.models import Integration
        from apps.integrations.tasks import sync_odoo_contacts

        # Check if integration exists
        integration = Integration.objects.filter(
            provider=Integration.Provider.ODOO,
            status=Integration.Status.ACTIVE
        ).first()

        if not integration:
            print("📝 Creating Odoo integration record...")
            # Create integration record
            integration = Integration.objects.create(
                name="North Cleaning Odoo CRM",
                provider=Integration.Provider.ODOO,
                status=Integration.Status.ACTIVE,
                team_id=1,  # Assuming a team exists
                created_by_id=1,  # Assuming admin user
                config={
                    'sync_frequency': 'daily',
                    'import_all_contacts': True
                }
            )

            # Store credentials
            integration.encrypt_credentials({
                'url': settings.ODOO_URL,
                'username': settings.ODOO_USERNAME,
                'api_key': settings.ODOO_API_KEY,
                'database': 'odoo'  # Default database name
            })
            integration.save()
            print(f"✅ Integration created with ID: {integration.id}")
        else:
            print(f"✅ Found existing integration: {integration.name}")

        # Test the sync task (run synchronously for testing)
        print("🔄 Running sync task...")
        result = sync_odoo_contacts(integration.id)

        print(f"✅ Sync completed: {result}")

    except Exception as e:
        print(f"❌ Sync task test failed: {e}")


if __name__ == "__main__":
    print("🚀 Starting Odoo Integration Tests for Hamburg Cleaning Services")
    print()

    # Test basic connection
    connection_success = test_odoo_connection()

    if connection_success:
        # Test sync task
        test_sync_task()

    print("\n" + "=" * 60)
    print("🏁 Odoo integration testing completed!")