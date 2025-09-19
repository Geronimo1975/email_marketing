"""
Test runner and coverage configuration for Email Marketing Platform.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
django.setup()


def run_tests():
    """Run all tests with coverage."""
    import coverage

    # Start coverage
    cov = coverage.Coverage()
    cov.start()

    try:
        # Run tests
        TestRunner = get_runner(settings)
        test_runner = TestRunner()
        failures = test_runner.run_tests(
            [
                "apps.accounts.tests",
                "apps.campaigns.tests",
                "apps.subscribers.tests",
                "apps.analytics.tests",
                "apps.automation.tests",
                "apps.integrations.tests",
                "tests.test_models",
                "tests.test_views",
                "tests.test_services",
                "tests.test_tasks",
                "tests.test_utils",
                "tests.test_integration",
                "tests.test_settings",
            ]
        )

        return failures
    finally:
        # Stop coverage and generate report
        cov.stop()
        cov.save()

        # Generate coverage report
        print("\n" + "=" * 50)
        print("COVERAGE REPORT")
        print("=" * 50)
        cov.report()

        # Generate HTML coverage report
        cov.html_report(directory="htmlcov")
        print(f"\nHTML coverage report generated in 'htmlcov' directory")

        # Generate XML coverage report for CI
        cov.xml_report(outfile="coverage.xml")
        print("XML coverage report generated as 'coverage.xml'")


if __name__ == "__main__":
    failures = run_tests()
    sys.exit(failures)
