from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Subscriber, SubscriberList, Tag, SegmentRule
from apps.analytics.models import EmailEvent, SubscriberActivity


def get_subscriber_stats(user):
    """
    Get subscriber statistics for a user.
    """
    # Get user's subscribers
    if user.is_admin:
        subscribers = Subscriber.objects.all()
    else:
        subscribers = Subscriber.objects.filter(
            Q(team__members=user) | Q(team__isnull=True)
        ).distinct()

    # Calculate basic stats
    total_subscribers = subscribers.count()
    active_subscribers = subscribers.filter(status=Subscriber.Status.SUBSCRIBED).count()
    unsubscribed_subscribers = subscribers.filter(
        status=Subscriber.Status.UNSUBSCRIBED
    ).count()
    bounced_subscribers = subscribers.filter(status=Subscriber.Status.BOUNCED).count()

    # Calculate monthly growth
    this_month = timezone.now().replace(day=1)
    new_this_month = subscribers.filter(created_at__gte=this_month).count()

    # Calculate engagement score average
    engagement_scores = subscribers.filter(engagement_score__isnull=False).aggregate(
        avg_score=Avg("engagement_score")
    )
    engagement_score_avg = engagement_scores["avg_score"] or 0

    # Get top tags
    top_tags = (
        Tag.objects.filter(subscribers__in=subscribers)
        .annotate(subscriber_count=Count("subscribers"))
        .order_by("-subscriber_count")[:5]
    )

    # Calculate growth rate (compared to last month)
    last_month = this_month - timedelta(days=1)
    last_month_start = last_month.replace(day=1)
    new_last_month = subscribers.filter(
        created_at__gte=last_month_start, created_at__lt=this_month
    ).count()

    growth_rate = 0
    if new_last_month > 0:
        growth_rate = ((new_this_month - new_last_month) / new_last_month) * 100

    return {
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "unsubscribed_subscribers": unsubscribed_subscribers,
        "bounced_subscribers": bounced_subscribers,
        "new_this_month": new_this_month,
        "engagement_score_avg": round(engagement_score_avg, 2),
        "top_tags": [
            {"name": tag.name, "count": tag.subscriber_count} for tag in top_tags
        ],
        "growth_rate": round(growth_rate, 2),
    }


def calculate_engagement_score(subscriber):
    """
    Calculate engagement score for a subscriber based on their activity.
    """
    score = 0
    max_score = 100

    # Email opens (40 points)
    open_events = EmailEvent.objects.filter(
        recipient_email=subscriber.email,
        event_type=EmailEvent.EventType.OPENED,
    ).count()
    score += min(open_events * 2, 40)  # 2 points per open, max 40

    # Email clicks (30 points)
    click_events = EmailEvent.objects.filter(
        recipient_email=subscriber.email,
        event_type=EmailEvent.EventType.CLICKED,
    ).count()
    score += min(click_events * 5, 30)  # 5 points per click, max 30

    # Recent activity (20 points)
    recent_activity = subscriber.last_activity
    if recent_activity:
        days_since_activity = (timezone.now() - recent_activity).days
        if days_since_activity <= 7:
            score += 20
        elif days_since_activity <= 30:
            score += 15
        elif days_since_activity <= 90:
            score += 10
        else:
            score += 5

    # Subscription duration (10 points)
    subscription_days = (timezone.now() - subscriber.created_at).days
    if subscription_days >= 365:
        score += 10
    elif subscription_days >= 180:
        score += 8
    elif subscription_days >= 90:
        score += 6
    elif subscription_days >= 30:
        score += 4
    else:
        score += 2

    # Update subscriber's engagement score
    subscriber.engagement_score = min(round(score), max_score)
    subscriber.save(update_fields=["engagement_score"])

    return subscriber.engagement_score


def segment_subscribers(rule):
    """
    Segment subscribers based on a rule.
    """
    field = rule.field
    operator = rule.operator
    value = rule.value

    # Start with all subscribers
    queryset = Subscriber.objects.all()

    # Apply field filter
    if field == "email":
        field_name = "email"
    elif field == "first_name":
        field_name = "first_name"
    elif field == "last_name":
        field_name = "last_name"
    elif field == "status":
        field_name = "status"
    elif field == "created_at":
        field_name = "created_at"
    elif field == "last_activity":
        field_name = "last_activity"
    else:
        return queryset.none()

    # Apply operator filter
    if operator == "equals":
        queryset = queryset.filter(**{f"{field_name}": value})
    elif operator == "contains":
        queryset = queryset.filter(**{f"{field_name}__icontains": value})
    elif operator == "starts_with":
        queryset = queryset.filter(**{f"{field_name}__istartswith": value})
    elif operator == "ends_with":
        queryset = queryset.filter(**{f"{field_name}__iendswith": value})
    elif operator == "is_empty":
        queryset = queryset.filter(**{f"{field_name}__isnull": True}) | queryset.filter(
            **{f"{field_name}": ""}
        )
    elif operator == "is_not_empty":
        queryset = queryset.filter(**{f"{field_name}__isnull": False}).exclude(
            **{f"{field_name}": ""}
        )
    elif operator == "greater_than":
        queryset = queryset.filter(**{f"{field_name}__gt": value})
    elif operator == "less_than":
        queryset = queryset.filter(**{f"{field_name}__lt": value})
    elif operator == "date_after":
        queryset = queryset.filter(**{f"{field_name}__gte": value})
    elif operator == "date_before":
        queryset = queryset.filter(**{f"{field_name}__lte": value})

    return queryset


def get_subscriber_engagement_trends(user, days=30):
    """
    Get subscriber engagement trends over time.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get user's subscribers
    if user.is_admin:
        subscribers = Subscriber.objects.all()
    else:
        subscribers = Subscriber.objects.filter(
            Q(team__members=user) | Q(team__isnull=True)
        ).distinct()

    # Get daily activity data
    daily_activity = (
        SubscriberActivity.objects.filter(
            subscriber__in=subscribers, date__gte=start_date
        )
        .values("date")
        .annotate(
            total_opens=Sum("opens"),
            total_clicks=Sum("clicks"),
            active_subscribers=Count("subscriber", distinct=True),
        )
        .order_by("date")
    )

    return list(daily_activity)


def get_top_engaged_subscribers(user, limit=10):
    """
    Get top engaged subscribers by engagement score.
    """
    if user.is_admin:
        subscribers = Subscriber.objects.filter(
            engagement_score__isnull=False
        ).order_by("-engagement_score")[:limit]
    else:
        subscribers = (
            Subscriber.objects.filter(
                Q(team__members=user) | Q(team__isnull=True),
                engagement_score__isnull=False,
            )
            .distinct()
            .order_by("-engagement_score")[:limit]
        )

    return subscribers


def get_subscriber_health_score(subscriber):
    """
    Calculate a health score for a subscriber based on various metrics.
    """
    score = 0
    max_score = 100

    # Engagement score (40 points)
    if subscriber.engagement_score:
        score += min(subscriber.engagement_score * 0.4, 40)

    # Recent activity (30 points)
    if subscriber.last_activity:
        days_since_activity = (timezone.now() - subscriber.last_activity).days
        if days_since_activity <= 7:
            score += 30
        elif days_since_activity <= 30:
            score += 25
        elif days_since_activity <= 90:
            score += 20
        else:
            score += 10

    # Subscription status (20 points)
    if subscriber.status == Subscriber.Status.SUBSCRIBED:
        score += 20
    elif subscriber.status == Subscriber.Status.UNSUBSCRIBED:
        score += 5
    else:
        score += 0

    # Email frequency (10 points)
    # This would be calculated based on how often they receive emails
    # For now, we'll give a base score
    score += 10

    return min(round(score), max_score)


def validate_subscriber_data(subscriber_data):
    """
    Validate subscriber data before import.
    """
    errors = []

    # Check required fields
    if not subscriber_data.get("email"):
        errors.append("Email is required")

    # Validate email format
    email = subscriber_data.get("email", "")
    if email and "@" not in email:
        errors.append("Invalid email format")

    # Check for duplicate email
    if email and Subscriber.objects.filter(email=email.lower()).exists():
        errors.append("Email already exists")

    return errors


def process_subscriber_import(
    file_content, list_id, update_existing=False, skip_duplicates=True
):
    """
    Process subscriber import from file content.
    """
    import csv
    import json
    from io import StringIO

    results = {
        "imported": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    try:
        # Parse CSV content
        csv_file = StringIO(file_content)
        reader = csv.DictReader(csv_file)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
            try:
                # Clean and validate data
                email = row.get("email", "").strip().lower()
                if not email:
                    results["errors"].append(f"Row {row_num}: Email is required")
                    continue

                # Check if subscriber exists
                subscriber, created = Subscriber.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": row.get("first_name", "").strip(),
                        "last_name": row.get("last_name", "").strip(),
                        "status": Subscriber.Status.SUBSCRIBED,
                    },
                )

                if created:
                    results["imported"] += 1
                else:
                    if update_existing:
                        subscriber.first_name = row.get("first_name", "").strip()
                        subscriber.last_name = row.get("last_name", "").strip()
                        subscriber.save()
                        results["updated"] += 1
                    else:
                        results["skipped"] += 1
                        continue

                # Add to list
                subscriber_list = SubscriberList.objects.get(id=list_id)
                subscriber.lists.add(subscriber_list)

                # Process custom fields
                custom_fields = {}
                for key, value in row.items():
                    if key not in ["email", "first_name", "last_name"] and value:
                        custom_fields[key] = value.strip()

                if custom_fields:
                    subscriber.custom_fields = custom_fields
                    subscriber.save()

            except Exception as e:
                results["errors"].append(f"Row {row_num}: {str(e)}")

    except Exception as e:
        results["errors"].append(f"File processing error: {str(e)}")

    return results


def export_subscribers_to_csv(list_id, fields=None):
    """
    Export subscribers to CSV format.
    """
    import csv
    from io import StringIO

    subscriber_list = SubscriberList.objects.get(id=list_id)
    subscribers = subscriber_list.subscribers.all()

    # Default fields
    if not fields:
        fields = ["email", "first_name", "last_name", "status", "created_at"]

    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(fields)

    # Write data
    for subscriber in subscribers:
        row = []
        for field in fields:
            if field == "custom_fields":
                # Handle custom fields
                if subscriber.custom_fields:
                    row.append(json.dumps(subscriber.custom_fields))
                else:
                    row.append("")
            else:
                value = getattr(subscriber, field, "")
                if hasattr(value, "isoformat"):  # Handle datetime fields
                    value = value.isoformat()
                row.append(str(value) if value else "")
        writer.writerow(row)

    return output.getvalue()


def sync_subscribers_with_odoo():
    """
    Sync subscribers with Odoo CRM.
    """
    from apps.integrations.services import OdooService

    try:
        odoo = OdooService()
        subscribers = Subscriber.objects.filter(odoo_contact_id__isnull=True)

        synced_count = 0
        for subscriber in subscribers:
            try:
                # Create contact in Odoo
                contact_data = {
                    "name": subscriber.full_name,
                    "email": subscriber.email,
                    "is_company": False,
                }

                contact_id = odoo.create_contact(contact_data)
                if contact_id:
                    subscriber.odoo_contact_id = contact_id
                    subscriber.save()
                    synced_count += 1

            except Exception as e:
                logger.error(f"Error syncing subscriber {subscriber.id}: {e}")

        return {"synced_count": synced_count, "status": "success"}

    except Exception as e:
        logger.error(f"Error syncing subscribers with Odoo: {e}")
        return {"synced_count": 0, "status": "error", "message": str(e)}
