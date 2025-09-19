# Django Email Marketing Platform

A production-ready Django email marketing platform with Mailgun API integration and Odoo CRM connectivity. Features campaign management, subscriber handling, automated workflows, and comprehensive analytics tracking.

## Features

- **Campaign Management**: Visual email template builder, A/B testing, scheduled sending
- **Subscriber Management**: Import/export, segmentation, GDPR compliance
- **Mailgun Integration**: Webhook endpoints, delivery tracking, suppression management
- **Odoo CRM Integration**: Bidirectional sync, lead scoring, automated workflows
- **Analytics**: Real-time dashboards, engagement tracking, ROI metrics
- **Automation**: Drip campaigns, behavioral targeting, workflow builder
- **Modern Frontend**: HTMX + Alpine.js + Tailwind CSS

## Tech Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL with Redis caching
- **Queue**: Celery with Redis broker
- **Frontend**: HTMX, Alpine.js, Tailwind CSS
- **Email**: Mailgun API
- **CRM**: Odoo API integration
- **Deployment**: Docker + Docker Compose

## Quick Start

### Using Docker (Recommended)

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd Email_marketing
   cp .env.example .env
   ```

2. **Configure environment** (edit `.env`):
   ```bash
   SECRET_KEY=your-secret-key-here
   MAILGUN_API_KEY=your-mailgun-api-key
   MAILGUN_DOMAIN=your-mailgun-domain.com
   ODOO_URL=https://your-odoo-instance.com
   ODOO_USERNAME=your-odoo-username
   ODOO_API_KEY=your-odoo-api-key
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Run migrations and create superuser**:
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Access the application**:
   - Web interface: http://localhost:8000
   - Admin panel: http://localhost:8000/admin
   - API endpoints: http://localhost:8000/api/

### Local Development

1. **Setup Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\\Scripts\\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # Install PostgreSQL and Redis locally, or use Docker:
   docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Start development server**:
   ```bash
   python manage.py runserver
   ```

6. **Start Celery workers** (in separate terminals):
   ```bash
   celery -A config worker -l info
   celery -A config beat -l info
   ```

## Project Structure

```
email_marketing/
├── config/                 # Django settings and configuration
│   ├── settings/          # Environment-specific settings
│   ├── celery.py          # Celery configuration
│   └── urls.py            # Main URL routing
├── apps/                  # Django applications
│   ├── accounts/          # User management and teams
│   ├── campaigns/         # Campaign management
│   ├── subscribers/       # Subscriber and list management
│   ├── analytics/         # Email tracking and reports
│   ├── integrations/      # Mailgun and Odoo APIs
│   └── automation/        # Workflow automation
├── templates/             # HTML templates
├── static/               # Static files (CSS, JS, images)
├── media/               # User uploaded files
└── tests/               # Test files
```

## Key Models

### Campaigns
- `Campaign`: Email campaigns with scheduling and A/B testing
- `EmailTemplate`: Reusable email templates
- `CampaignRecipient`: Individual recipient tracking

### Subscribers
- `Subscriber`: Email subscribers with engagement tracking
- `SubscriberList`: Segmented subscriber lists
- `Tag`: Tagging system for organization

### Analytics
- `EmailEvent`: Mailgun webhook events (opens, clicks, bounces)
- `CampaignReport`: Aggregated campaign performance
- `SubscriberActivity`: Individual engagement metrics

### Integrations
- `Integration`: External service configurations
- `WebhookEndpoint`: Webhook URL management
- `SyncJob`: Background synchronization tasks

## API Endpoints

### Authentication
- `POST /api/auth/login/` - User authentication
- `POST /api/auth/logout/` - User logout

### Campaigns
- `GET /api/campaigns/` - List campaigns
- `POST /api/campaigns/` - Create campaign
- `GET /api/campaigns/{id}/` - Campaign details
- `POST /api/campaigns/{id}/send/` - Send campaign

### Subscribers
- `GET /api/subscribers/` - List subscribers
- `POST /api/subscribers/` - Create subscriber
- `POST /api/subscribers/import/` - Bulk import

### Analytics
- `GET /api/analytics/dashboard/` - Analytics dashboard
- `GET /api/campaigns/{id}/stats/` - Campaign statistics

### Webhooks
- `POST /webhooks/mailgun/` - Mailgun delivery events
- `POST /webhooks/odoo/` - Odoo CRM updates

## Background Tasks

The platform uses Celery for background processing:

- **Email sending**: Bulk email delivery via Mailgun
- **Webhook processing**: Email event tracking
- **Automation workflows**: Drip campaigns and triggers
- **Data synchronization**: Odoo CRM integration
- **Analytics updates**: Engagement score calculations

## Security Features

- CSRF protection on all forms
- Rate limiting on API endpoints
- Input validation and sanitization
- Secure API key management
- Permission-based access control
- SQL injection prevention

## Monitoring & Observability

- Structured logging with Django logging
- Celery task monitoring
- Email deliverability tracking
- Performance metrics collection
- Error tracking with Sentry (in production)

## Deployment

### Production Deployment

1. **Environment variables**:
   ```bash
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   REDIS_URL=redis://host:6379/0
   SECRET_KEY=production-secret-key
   SENTRY_DSN=your-sentry-dsn
   ```

2. **Docker deployment**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **SSL/TLS**:
   - Configure reverse proxy (Nginx)
   - Setup SSL certificates
   - Enable security headers

## Testing

Run the test suite:
```bash
python manage.py test
```

With coverage:
```bash
pip install coverage
coverage run manage.py test
coverage report
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the documentation
- Review the issue tracker
- Contact the development team

---

**Note**: This is a comprehensive email marketing platform. Ensure you comply with email marketing regulations (CAN-SPAM, GDPR, etc.) when using this system.