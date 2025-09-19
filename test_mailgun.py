#!/usr/bin/env python
"""
Test script for Mailgun connection
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.integrations.services import MailgunService
from django.conf import settings

def test_mailgun_connection():
    """Test Mailgun API connection and configuration."""
    print("Testing Mailgun connection...")
    print(f"Domain: {settings.MAILGUN_DOMAIN}")
    print(f"API Key: {'*' * 20}{settings.MAILGUN_API_KEY[-10:] if settings.MAILGUN_API_KEY else 'NOT SET'}")

    try:
        # Initialize Mailgun service
        mailgun = MailgunService()
        print("✓ Mailgun service initialized successfully")

        # Test domain verification by trying to get events
        print("\nTesting domain access...")
        events = mailgun.get_events(limit=1)
        print(f"✓ Successfully accessed domain. Recent events: {len(events)}")

        # Test email validation API
        print("\nTesting email validation...")
        test_email = "test@example.com"
        validation_result = mailgun.validate_email(test_email)
        print(f"✓ Email validation API working. Result for {test_email}: {validation_result.get('result', 'unknown')}")

        # Test getting suppressions
        print("\nTesting suppression lists...")
        bounces = mailgun.get_suppressions('bounces')
        print(f"✓ Bounces list accessible. Count: {len(bounces)}")

        print("\n🎉 All Mailgun tests passed! Configuration is working correctly.")
        return True

    except Exception as e:
        print(f"\n❌ Mailgun test failed: {str(e)}")
        return False

def test_send_email():
    """Test sending a simple email."""
    print("\n" + "="*50)
    print("OPTIONAL: Test sending email")
    print("="*50)

    response = input("Do you want to test sending an email? (y/N): ").lower().strip()
    if response != 'y':
        print("Skipping email send test.")
        return True

    to_email = input("Enter recipient email address: ").strip()
    if not to_email:
        print("No email provided. Skipping send test.")
        return True

    try:
        mailgun = MailgunService()

        result = mailgun.send_email(
            to_email=to_email,
            subject="Test Email from Django Email Marketing Platform",
            html_content="""
            <h2>Hello from Django Email Marketing!</h2>
            <p>This is a test email to verify your Mailgun integration is working correctly.</p>
            <p>If you received this email, your configuration is successful!</p>
            <br>
            <p><small>This email was sent via Mailgun API from your Django application.</small></p>
            """,
            text_content="Hello! This is a test email from your Django Email Marketing platform. If you received this, your Mailgun integration is working!",
            from_name="Email Marketing Platform",
            tags=["test", "mailgun-verification"]
        )

        print(f"✓ Email sent successfully!")
        print(f"Message ID: {result.get('id', 'N/A')}")
        print(f"Message: {result.get('message', 'N/A')}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

if __name__ == '__main__':
    print("Django Email Marketing - Mailgun Connection Test")
    print("=" * 50)

    # Test basic connection
    connection_ok = test_mailgun_connection()

    if connection_ok:
        # Optionally test sending
        test_send_email()

    print("\nTest completed!")