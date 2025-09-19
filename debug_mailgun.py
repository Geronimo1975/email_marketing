#!/usr/bin/env python3
"""
Debug Mailgun domain and API key
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_mailgun():
    """Debug Mailgun configuration."""

    api_key = os.getenv('MAILGUN_API_KEY')
    domain = os.getenv('MAILGUN_DOMAIN')

    print("=" * 60)
    print("MAILGUN DEBUG INFORMATION")
    print("=" * 60)

    print(f"API Key: {api_key}")
    print(f"Domain: {domain}")
    print()

    # Test 1: List all domains for this API key
    print("Test 1: List all domains for this API key")
    print("-" * 50)
    try:
        url = "https://api.mailgun.net/v3/domains"
        auth = ('api', api_key)

        response = requests.get(url, auth=auth, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            domains_data = response.json()
            domains = domains_data.get('items', [])
            print(f"✓ Found {len(domains)} domain(s):")
            for i, domain_info in enumerate(domains, 1):
                print(f"  {i}. Name: {domain_info.get('name', 'N/A')}")
                print(f"     State: {domain_info.get('state', 'N/A')}")
                print(f"     Type: {domain_info.get('type', 'N/A')}")
                print()
        else:
            print(f"❌ Failed to list domains: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")

    print()

    # Test 2: Try to get domain info directly
    print("Test 2: Check specific domain info")
    print("-" * 50)
    try:
        url = f"https://api.mailgun.net/v3/domains/{domain}"
        auth = ('api', api_key)

        response = requests.get(url, auth=auth, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            domain_data = response.json()
            domain_info = domain_data.get('domain', {})
            print(f"✓ Domain found:")
            print(f"  Name: {domain_info.get('name', 'N/A')}")
            print(f"  State: {domain_info.get('state', 'N/A')}")
            print(f"  Type: {domain_info.get('type', 'N/A')}")
            print(f"  Created: {domain_info.get('created_at', 'N/A')}")
        elif response.status_code == 404:
            print(f"❌ Domain '{domain}' not found")
            print("This could mean:")
            print("  - Domain name is incorrect")
            print("  - Domain is not added to this Mailgun account")
            print("  - API key doesn't have access to this domain")
        else:
            print(f"❌ Failed to get domain info: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")

    print()

    # Test 3: Test API key authentication
    print("Test 3: Test API key authentication")
    print("-" * 50)
    try:
        url = "https://api.mailgun.net/v3/domains"
        auth = ('api', api_key)

        response = requests.get(url, auth=auth, timeout=10)

        if response.status_code == 401:
            print("❌ API key authentication failed")
            print("Check if your API key is correct")
        elif response.status_code == 200:
            print("✓ API key authentication successful")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")

if __name__ == '__main__':
    debug_mailgun()