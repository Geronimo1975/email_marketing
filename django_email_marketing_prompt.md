# Django Email Marketing System with Mailgun & Odoo Integration

## Project Overview
Create a production-ready Django email marketing platform with Mailgun API integration and Odoo CRM connectivity. The system should support campaign management, subscriber handling, automated workflows, and comprehensive analytics tracking.

## Core Requirements

### Django Application Structure
- **Multi-app Django project** with clear separation of concerns
- **campaigns/** - Campaign management and scheduling
- **subscribers/** - Contact list and subscriber management  
- **analytics/** - Email tracking and performance metrics
- **integrations/** - Mailgun and Odoo API handlers
- **automation/** - Workflow triggers and email sequences
- **accounts/** - User management and team permissions

### Frontend Technology Stack
- **HTMX** for dynamic UI interactions without page reloads
- **Alpine.js** for lightweight JavaScript interactions
- **Tailwind CSS** or Bootstrap 5 for responsive design
- **Chart.js** for analytics dashboards
- **Django templates** with template inheritance and includes

### Database Architecture
- **PostgreSQL** as primary database
- **Redis** for caching and background task queuing
- **Proper model relationships** with foreign keys and many-to-many fields
- **Database indexes** on frequently queried fields
- **Migration files** for all model changes

## Key Features to Implement

### 1. Campaign Management System
- Visual email template builder with drag-drop components
- A/B testing functionality for subject lines and content
- Scheduled sending with timezone support
- Campaign duplication and template library
- Responsive email preview across devices
- Dynamic content personalization using subscriber data

### 2. Subscriber Management
- Import/export functionality (CSV, Excel formats)
- Segmentation rules based on subscriber attributes
- Subscription preferences and unsubscribe handling
- Double opt-in confirmation workflows
- Subscriber activity tracking and engagement scoring
- GDPR compliance features (data export, deletion)

### 3. Mailgun Integration
- **Webhook endpoints** for delivery status, opens, clicks, bounces
- **Domain verification** and DNS record validation
- **Suppression list management** (bounces, complaints, unsubscribes)
- **Email validation API** integration for list cleaning
- **Rate limiting** to respect Mailgun API limits
- **Retry mechanisms** for failed API calls

### 4. Odoo CRM Integration
- **Bidirectional sync** of contacts and leads
- **Custom field mapping** between Odoo and email platform
- **Lead scoring** integration with email engagement data
- **Automated workflows** triggered by Odoo events
- **Sales pipeline updates** based on email interactions
- **OAuth2 authentication** for secure Odoo API access

### 5. Analytics & Reporting
- Real-time campaign performance dashboards
- Email deliverability metrics and trends
- Subscriber engagement heatmaps
- ROI tracking with conversion attribution
- Automated report generation and email delivery
- Export capabilities for external analysis

### 6. Automation Workflows
- **Drip campaigns** with conditional branching
- **Trigger-based sequences** (welcome series, abandoned cart)
- **Behavioral targeting** based on subscriber actions
- **Integration with external webhooks** for advanced automation
- **Workflow visual builder** for non-technical users

## Technical Implementation Requirements

### Django Best Practices
- **Class-based views** with proper mixins
- **Django REST Framework** for API endpoints
- **Celery** with Redis broker for background tasks
- **Django signals** for event-driven architecture
- **Custom management commands** for data processing
- **Proper error handling** with logging and monitoring

### Security Implementation
- **CSRF protection** on all forms
- **Rate limiting** on API endpoints
- **User authentication** with permission-based access control
- **Secure API key management** using environment variables
- **Input validation** and sanitization
- **SQL injection prevention** with parameterized queries

### Performance Optimization
- **Database query optimization** with select_related and prefetch_related
- **Caching strategies** for frequently accessed data
- **Pagination** for large datasets
- **Background task processing** for heavy operations
- **CDN integration** for static assets
- **Database connection pooling**

### Testing Strategy
- **Unit tests** for models, views, and utilities
- **Integration tests** for API endpoints
- **Mock external API calls** (Mailgun, Odoo)
- **Test fixtures** for consistent test data
- **Coverage reporting** with minimum 90% coverage
- **Automated testing** in CI/CD pipeline

## File Structure Requirements

```
email_marketing/
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── campaigns/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── tasks.py
│   │   └── templates/
│   ├── subscribers/
│   ├── analytics/
│   ├── integrations/
│   ├── automation/
│   └── accounts/
├── static/
├── templates/
├── media/
├── tests/
└── docs/
```

## Environment Configuration

### Required Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection for caching and Celery
- `MAILGUN_API_KEY` - Mailgun API authentication
- `MAILGUN_DOMAIN` - Verified Mailgun domain
- `ODOO_URL` - Odoo instance URL
- `ODOO_USERNAME` - Odoo API username
- `ODOO_API_KEY` - Odoo API key
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode setting
- `ALLOWED_HOSTS` - Allowed host domains

### Docker Configuration
- Multi-stage Dockerfile for optimization
- Docker Compose for local development
- Separate services for Django, PostgreSQL, Redis, and Celery
- Volume mounts for development file watching
- Environment file integration

## API Design Requirements

### Webhook Endpoints
- `/webhooks/mailgun/` - Handle Mailgun delivery events
- `/webhooks/odoo/` - Process Odoo CRM updates
- `/api/campaigns/{id}/stats/` - Real-time campaign statistics
- `/api/subscribers/import/` - Bulk subscriber import
- `/api/automation/trigger/` - External workflow triggers

### Authentication & Permissions
- Token-based API authentication
- Role-based permissions (Admin, Campaign Manager, Viewer)
- Rate limiting per user/IP
- API versioning for future compatibility

## Deployment Considerations

### Production Requirements
- **Gunicorn** WSGI server configuration
- **Nginx** reverse proxy setup
- **SSL certificate** configuration
- **Static file serving** with whitenoise or CDN
- **Database connection pooling**
- **Log aggregation** with structured logging
- **Health check endpoints** for monitoring
- **Backup automation** for database and media files

### Monitoring & Observability
- **Application monitoring** with Sentry
- **Performance tracking** with New Relic or similar
- **Custom metrics** for email deliverability
- **Alert configuration** for system failures
- **Dashboard creation** for operational metrics

## Specific Implementation Instructions

1. **Start with Django project setup** using the latest LTS version
2. **Configure PostgreSQL** with proper indexing strategy
3. **Implement Mailgun wrapper classes** with proper error handling
4. **Create Odoo API client** with OAuth2 authentication
5. **Build HTMX-powered frontend** with progressive enhancement
6. **Add Celery task processing** for background operations
7. **Implement comprehensive testing suite**
8. **Create deployment scripts** and documentation
9. **Add monitoring and logging** throughout the application

## Code Quality Standards
- **PEP 8 compliance** with Black formatter
- **Type hints** for all function parameters and returns
- **Docstrings** for all classes and methods
- **Import organization** with isort
- **Security scanning** with bandit
- **Dependency vulnerability scanning**

Generate a complete, production-ready Django application that demonstrates enterprise-level email marketing platform development with proper architecture, security, and scalability considerations.