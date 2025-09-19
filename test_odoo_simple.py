#!/usr/bin/env python
"""
Simple Odoo integration test without complex model dependencies
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.subscribers.models import EmailContact
from apps.integrations.services import OdooService
from django.conf import settings


def test_odoo_and_import_contacts():
    """Test Odoo connection and import some contacts."""
    print("🔌 Testing Odoo Connection & Importing Contacts")
    print("=" * 50)

    try:
        # Initialize Odoo service
        print("🔧 Initializing Odoo service...")
        odoo_service = OdooService()
        print(f"✅ Connected to: {settings.ODOO_URL}")
        print(f"📊 Database: {settings.ODOO_DATABASE}")

        # Test authentication
        print("\n🔐 Testing authentication...")
        uid = odoo_service._authenticate()
        print(f"✅ Authentication successful! User ID: {uid}")

        # Search for contacts
        print("\n👥 Searching for contacts in Odoo...")
        contact_ids = odoo_service.search_contacts(
            domain=[['email', '!=', False]],  # Only contacts with emails
            limit=5  # Limit to 5 for testing
        )
        print(f"✅ Found {len(contact_ids)} contacts with email addresses")

        if not contact_ids:
            print("ℹ️  No contacts found with email addresses")
            return

        # Get contact details
        print("\n📋 Retrieving contact details...")
        contacts = odoo_service.get_contacts(contact_ids)
        print(f"✅ Retrieved {len(contacts)} contact records")

        # Show current database state
        existing_count = EmailContact.objects.count()
        print(f"\n📊 Current email contacts in database: {existing_count}")

        # Import contacts
        print("\n📥 Importing contacts into email marketing system...")
        imported_count = 0
        updated_count = 0

        for contact_data in contacts:
            try:
                email = contact_data.get('email')
                if not email:
                    continue

                # Parse name
                name = contact_data.get('name', '')
                name_parts = name.split(' ') if name else ['', '']

                # Determine if it's a company
                is_company = contact_data.get('is_company', False)

                # Set first_name and last_name based on company status
                if is_company:
                    first_name = ''
                    last_name = ''
                    company_name = name
                else:
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    company_name = ''

                # Create or update contact (simplified without team)
                contact_obj, created = EmailContact.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'company_name': company_name,
                        'phone': contact_data.get('phone') or contact_data.get('mobile', ''),
                        'address': contact_data.get('street', ''),
                        'postal_code': contact_data.get('zip', ''),
                        'source': 'Odoo Import',
                        'odoo_contact_id': contact_data.get('id'),
                        'gdpr_consent': True,  # Assume consent from CRM
                        'is_subscribed': True,
                        'business_type': EmailContact.BusinessType.OFFICE_BUILDING if is_company else EmailContact.BusinessType.OTHER,
                        'hamburg_district': EmailContact.HamburgDistrict.HAMBURG_MITTE,  # Default
                    }
                )

                if created:
                    imported_count += 1
                    print(f"   ✅ Imported: {email} ({name})")
                else:
                    # Update Odoo ID if missing
                    if not contact_obj.odoo_contact_id:
                        contact_obj.odoo_contact_id = contact_data.get('id')
                        contact_obj.save()
                        updated_count += 1
                        print(f"   🔄 Updated: {email} (added Odoo ID)")

            except Exception as e:
                print(f"   ❌ Failed to import {contact_data.get('email', 'Unknown')}: {e}")

        # Show results
        print(f"\n📊 Import Results:")
        print(f"   ✅ New contacts imported: {imported_count}")
        print(f"   🔄 Existing contacts updated: {updated_count}")
        print(f"   📈 Total contacts now: {EmailContact.objects.count()}")

        # Show sample imported contacts
        if imported_count > 0 or updated_count > 0:
            print(f"\n👥 Sample contacts from Odoo:")
            recent_contacts = EmailContact.objects.filter(
                source='Odoo Import'
            )[:3]

            for i, contact in enumerate(recent_contacts, 1):
                name = f"{contact.first_name} {contact.last_name}".strip() or contact.company_name
                print(f"   {i}. {name}")
                print(f"      📧 Email: {contact.email}")
                print(f"      🏢 Company: {contact.company_name}")
                print(f"      📞 Phone: {contact.phone}")
                print(f"      🆔 Odoo ID: {contact.odoo_contact_id}")
                print()

        print("🎉 Odoo integration test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 North Cleaning Services - Simple Odoo Test")
    print()
    test_odoo_and_import_contacts()