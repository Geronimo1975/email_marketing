#!/usr/bin/env python
"""
Fixed Odoo integration test with proper database discovery
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.integrations.services import OdooService
from django.conf import settings
import xmlrpc.client


def discover_odoo_database():
    """Discover available databases on the Odoo server."""
    print("🔍 Discovering available databases...")

    try:
        # Connect to Odoo server info
        common = xmlrpc.client.ServerProxy(f'{settings.ODOO_URL}/xmlrpc/2/common')

        # Get server version info
        version_info = common.version()
        print(f"✅ Connected to Odoo server: {version_info}")

        # Try to get database list
        db_list = xmlrpc.client.ServerProxy(f'{settings.ODOO_URL}/xmlrpc/2/db')
        try:
            databases = db_list.list()
            print(f"📋 Available databases: {databases}")
            return databases
        except Exception as e:
            print(f"⚠️  Could not list databases: {e}")
            # Common database names to try
            return ['prod', 'main', 'ncsg', 'north-cleaning', 'northcleaning']

    except Exception as e:
        print(f"❌ Failed to connect to Odoo server: {e}")
        return []


def test_odoo_with_database(database_name):
    """Test Odoo connection with a specific database."""
    print(f"\n🔌 Testing Odoo with database: {database_name}")
    print("-" * 50)

    try:
        # Create OdooService with specific database
        odoo_service = OdooService(database=database_name)

        # Test authentication
        print("🔐 Testing authentication...")
        uid = odoo_service._authenticate()

        if uid:
            print(f"✅ Authentication successful! User ID: {uid}")
            return True, odoo_service
        else:
            print("❌ Authentication failed")
            return False, None

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None


def test_basic_operations(odoo_service):
    """Test basic Odoo operations."""
    print("\n📊 Testing basic operations...")

    try:
        # Test contact search with simple domain
        print("👥 Searching for contacts...")
        contact_ids = odoo_service.search_contacts(
            domain=[['email', '!=', False]],
            limit=3
        )
        print(f"✅ Found {len(contact_ids)} contacts with emails")

        if contact_ids:
            # Get contact details
            contacts = odoo_service.get_contacts(contact_ids)
            print(f"✅ Retrieved {len(contacts)} contact records")

            for i, contact in enumerate(contacts, 1):
                print(f"\n📧 Contact {i}:")
                print(f"   ID: {contact.get('id')}")
                print(f"   Name: {contact.get('name', 'N/A')}")
                print(f"   Email: {contact.get('email', 'N/A')}")
                print(f"   Is Company: {contact.get('is_company', False)}")

        return True

    except Exception as e:
        print(f"❌ Operations failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 North Cleaning Services - Odoo Integration Test")
    print("=" * 60)

    print(f"📍 Odoo URL: {settings.ODOO_URL}")
    print(f"👤 Username: {settings.ODOO_USERNAME}")
    print(f"🔑 API Key: {'*' * 20}...{settings.ODOO_API_KEY[-8:]}")

    # Discover databases
    databases = discover_odoo_database()

    if not databases:
        print("❌ No databases found. Cannot proceed with testing.")
        return

    # Test each database
    for db_name in databases:
        success, odoo_service = test_odoo_with_database(db_name)

        if success:
            print(f"🎉 Successfully connected to database: {db_name}")

            # Test basic operations
            operations_success = test_basic_operations(odoo_service)

            if operations_success:
                print(f"\n✅ All tests passed for database: {db_name}")

                # Update .env file with correct database
                print(f"\n📝 Updating .env file with database: {db_name}")
                update_env_file(db_name)
                return

        print(f"❌ Failed to connect to database: {db_name}")

    print("\n❌ Could not establish connection to any Odoo database")


def update_env_file(database_name):
    """Update .env file with correct database name."""
    try:
        # Read current .env file
        with open('.env', 'r') as f:
            lines = f.readlines()

        # Add ODOO_DATABASE line
        new_lines = []
        database_added = False

        for line in lines:
            new_lines.append(line)
            if line.startswith('ODOO_API_KEY=') and not database_added:
                new_lines.append(f'ODOO_DATABASE={database_name}\n')
                database_added = True

        # Write updated .env file
        with open('.env', 'w') as f:
            f.writelines(new_lines)

        print(f"✅ Updated .env with ODOO_DATABASE={database_name}")

    except Exception as e:
        print(f"⚠️  Could not update .env file: {e}")


if __name__ == "__main__":
    main()