#!/usr/bin/env python
"""
Test runner script for Email Marketing Platform.
"""

import os
import sys
import subprocess
import django
from django.conf import settings

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
django.setup()


def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)

    return result.returncode == 0


def main():
    """Main test runner function."""
    print("🚀 Starting Email Marketing Platform Test Suite")
    print("=" * 60)

    # Test commands
    commands = [
        ("python -m pytest tests/ -v --tb=short", "Unit and Integration Tests"),
        ("python -m pytest tests/test_models.py -v", "Model Tests"),
        ("python -m pytest tests/test_views.py -v", "View Tests"),
        ("python -m pytest tests/test_services.py -v", "Service Tests"),
        ("python -m pytest tests/test_tasks.py -v", "Task Tests"),
        ("python -m pytest tests/test_utils.py -v", "Utility Tests"),
        ("python -m pytest tests/test_integration.py -v", "Integration Tests"),
        ("python -m pytest tests/test_settings.py -v", "Settings Tests"),
        (
            "python -m pytest tests/ --cov=apps --cov-report=html --cov-report=term-missing",
            "Coverage Report",
        ),
        (
            "python -m flake8 apps/ --max-line-length=100 --exclude=migrations",
            "Code Quality Check",
        ),
        ("python -m black --check apps/", "Code Formatting Check"),
        ("python -m isort --check-only apps/", "Import Sorting Check"),
    ]

    success_count = 0
    total_count = len(commands)

    for command, description in commands:
        if run_command(command, description):
            success_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {success_count}/{total_count}")
    print(f"❌ Failed: {total_count - success_count}/{total_count}")

    if success_count == total_count:
        print("🎉 All tests passed! The codebase is ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review and fix the issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
