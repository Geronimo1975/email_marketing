#!/usr/bin/env python3
"""
Simple Mailgun connection test without Django
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mailgun_connection():
    """Test Mailgun API connection."""

    # Get credentials from environment
    api_key = os.getenv('MAILGUN_API_KEY')
    domain = os.getenv('MAILGUN_DOMAIN')

    print("=" * 60)
    print("MAILGUN CONNECTION TEST")
    print("=" * 60)

    if not api_key:
        print("❌ MAILGUN_API_KEY not found in environment")
        return False

    if not domain:
        print("❌ MAILGUN_DOMAIN not found in environment")
        return False

    print(f"✓ Domain: {domain}")
    print(f"✓ API Key: {'*' * 20}{api_key[-10:] if len(api_key) >= 10 else api_key}")
    print()

    # Test 1: Domain verification via events API
    print("Test 1: Domain Access via Events API")
    print("-" * 40)
    try:
        url = f"https://api.mailgun.net/v3/{domain}/events"
        auth = ('api', api_key)
        params = {'limit': 1}

        response = requests.get(url, auth=auth, params=params, timeout=10)

        if response.status_code == 200:
            events_data = response.json()
            events_count = len(events_data.get('items', []))
            print(f"✓ Successfully accessed domain events API")
            print(f"✓ Recent events found: {events_count}")
        elif response.status_code == 401:
            print("❌ Authentication failed - check your API key")
            return False
        elif response.status_code == 404:
            print("❌ Domain not found - check your domain name")
            return False
        else:
            print(f"❌ API returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

    print()

    # Test 2: Email validation API
    print("Test 2: Email Validation API")
    print("-" * 40)
    try:
        url = "https://api.mailgun.net/v4/address/validate"
        auth = ('api', api_key)
        params = {'address': 'test@example.com'}

        response = requests.get(url, auth=auth, params=params, timeout=10)

        if response.status_code == 200:
            validation_data = response.json()
            result = validation_data.get('result', 'unknown')
            print(f"✓ Email validation API working")
            print(f"✓ Validation result for test@example.com: {result}")
        else:
            print(f"⚠️  Email validation API returned: {response.status_code}")
            print("(This might be a plan limitation)")

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Email validation test failed: {e}")

    print()

    # Test 3: Domain stats (if available)
    print("Test 3: Domain Stats")
    print("-" * 40)
    try:
        url = f"https://api.mailgun.net/v3/{domain}/stats/total"
        auth = ('api', api_key)

        response = requests.get(url, auth=auth, timeout=10)

        if response.status_code == 200:
            stats_data = response.json()
            print(f"✓ Domain stats accessible")
            print(f"✓ Stats data available: {bool(stats_data.get('stats'))}")
        else:
            print(f"⚠️  Domain stats returned: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"⚠️  Domain stats test failed: {e}")

    print()
    print("🎉 Basic Mailgun connectivity tests completed!")
    print("✅ Your Mailgun configuration appears to be working correctly.")
    return True

def test_send_email():
    """Test sending a real email."""
    print("\n" + "=" * 60)
    print("EMAIL SENDING TEST (OPTIONAL)")
    print("=" * 60)

    response = input("Do you want to test sending an actual email? (y/N): ").strip().lower()
    if response != 'y':
        print("Skipping email send test.")
        return True

    to_email = input("Enter recipient email address: ").strip()
    if not to_email:
        print("No email provided. Skipping send test.")
        return True

    api_key = os.getenv('MAILGUN_API_KEY')
    domain = os.getenv('MAILGUN_DOMAIN')

    try:
        url = f"https://api.mailgun.net/v3/{domain}/messages"
        auth = ('api', api_key)

        data = {
            'from': f'Email Marketing Test <noreply@{domain}>',
            'to': to_email,
            'subject': 'Test Email from Django Email Marketing Platform',
            'html': '''
            <html>
            <body>
                <h2>Hello from Django Email Marketing! 🚀</h2>
                <p>This is a test email to verify your Mailgun integration is working correctly.</p>
                <p>If you received this email, your configuration is successful!</p>
                <br>
                <p><small>This email was sent via Mailgun API from your Django application.</small></p>
            </body>
            </html>
            ''',
            'text': 'Hello! This is a test email from your Django Email Marketing platform. If you received this, your Mailgun integration is working!',
            'o:tag': ['test', 'mailgun-verification'],
            'o:tracking': 'yes',
            'o:tracking-clicks': 'yes',
            'o:tracking-opens': 'yes'
        }

        response = requests.post(url, auth=auth, data=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Email sent successfully!")
            print(f"📧 Message ID: {result.get('id', 'N/A')}")
            print(f"📝 Message: {result.get('message', 'N/A')}")
            print(f"📬 Sent to: {to_email}")
            return True
        else:
            print(f"❌ Failed to send email. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending email: {e}")
        return False

if __name__ == '__main__':
    # Run connection tests
    connection_ok = test_mailgun_connection()

    if connection_ok:
        # Optionally test sending
        test_send_email()

    print("\n" + "=" * 60)
    print("TEST COMPLETED!")
    print("=" * 60)