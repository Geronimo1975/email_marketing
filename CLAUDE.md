# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Django email marketing platform project that is planned but not yet implemented. The project will integrate with Mailgun for email delivery and Odoo CRM for contact management.

## Planned Architecture
The project will follow a multi-app Django structure:
- **campaigns/** - Campaign management and scheduling
- **subscribers/** - Contact list and subscriber management
- **analytics/** - Email tracking and performance metrics
- **integrations/** - Mailgun and Odoo API handlers
- **automation/** - Workflow triggers and email sequences
- **accounts/** - User management and team permissions

## Technology Stack
- **Backend**: Django (latest LTS) with Django REST Framework
- **Database**: PostgreSQL with Redis for caching
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Background Tasks**: Celery with Redis broker
- **Email Service**: Mailgun API
- **CRM Integration**: Odoo API with OAuth2

## Development Commands
**Project Setup:**
- `python manage.py check` - Check Django configuration
- `python manage.py migrate` - Apply database migrations
- `python manage.py createsuperuser` - Create admin user
- `python manage.py collectstatic` - Collect static files

**Development Server:**
- `python manage.py runserver` - Start development server
- `celery -A config worker -l info` - Start Celery worker
- `celery -A config beat -l info` - Start Celery beat scheduler

**Docker Commands:**
- `docker-compose up -d` - Start all services
- `docker-compose exec web python manage.py migrate` - Run migrations in container
- `docker-compose logs web` - View Django logs
- `docker-compose down` - Stop all services

**Testing:**
- `python manage.py test` - Run test suite
- `python manage.py test apps.campaigns` - Test specific app

## Code Quality Standards
- PEP 8 compliance with Black formatter
- Type hints for all function parameters and returns
- Docstrings for all classes and methods
- Import organization with isort
- 90% minimum test coverage requirement

## Key Integration Points
- **Mailgun webhooks**: `/webhooks/mailgun/` for delivery events
- **Odoo webhooks**: `/webhooks/odoo/` for CRM updates
- **API endpoints**: Token-based authentication with role permissions
- **Background tasks**: All heavy operations (email sending, imports) via Celery

## Environment Variables Required
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `MAILGUN_API_KEY` and `MAILGUN_DOMAIN` - Email service
- `ODOO_URL`, `ODOO_USERNAME`, `ODOO_API_KEY` - CRM integration
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` - Django config

## Security Considerations
- CSRF protection on all forms
- Rate limiting on API endpoints
- Input validation and sanitization
- Secure API key management via environment variables
- Permission-based access control