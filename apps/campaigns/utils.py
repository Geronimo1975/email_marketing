from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Campaign
from apps.analytics.models import EmailEvent, CampaignReport


def get_campaign_stats(user):
    """
    Get campaign statistics for a user.
    """
    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Calculate basic stats
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(status=Campaign.Status.SENDING).count()
    scheduled_campaigns = campaigns.filter(status=Campaign.Status.SCHEDULED).count()
    draft_campaigns = campaigns.filter(status=Campaign.Status.DRAFT).count()

    # Calculate email stats
    total_emails_sent = campaigns.aggregate(total=Sum("emails_sent"))["total"] or 0

    total_emails_delivered = (
        campaigns.aggregate(total=Sum("emails_delivered"))["total"] or 0
    )

    total_emails_opened = campaigns.aggregate(total=Sum("emails_opened"))["total"] or 0

    total_emails_clicked = (
        campaigns.aggregate(total=Sum("emails_clicked"))["total"] or 0
    )

    # Calculate rates
    open_rate = 0
    click_rate = 0
    delivery_rate = 0

    if total_emails_delivered > 0:
        open_rate = (total_emails_opened / total_emails_delivered) * 100
        click_rate = (total_emails_clicked / total_emails_delivered) * 100

    if total_emails_sent > 0:
        delivery_rate = (total_emails_delivered / total_emails_sent) * 100

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "scheduled_campaigns": scheduled_campaigns,
        "draft_campaigns": draft_campaigns,
        "total_emails_sent": total_emails_sent,
        "total_emails_delivered": total_emails_delivered,
        "total_emails_opened": total_emails_opened,
        "total_emails_clicked": total_emails_clicked,
        "open_rate": round(open_rate, 2),
        "click_rate": round(click_rate, 2),
        "delivery_rate": round(delivery_rate, 2),
    }


def calculate_engagement_metrics(campaign):
    """
    Calculate detailed engagement metrics for a campaign.
    """
    # Get all email events for this campaign
    events = EmailEvent.objects.filter(campaign=campaign)

    # Basic metrics
    total_recipients = campaign.total_recipients
    emails_sent = campaign.emails_sent
    emails_delivered = campaign.emails_delivered
    emails_bounced = campaign.emails_bounced
    emails_opened = campaign.emails_opened
    emails_clicked = campaign.emails_clicked
    unsubscribes = campaign.unsubscribes
    complaints = campaign.complaints

    # Calculate rates
    open_rate = (emails_opened / emails_delivered * 100) if emails_delivered > 0 else 0
    click_rate = (
        (emails_clicked / emails_delivered * 100) if emails_delivered > 0 else 0
    )
    bounce_rate = (emails_bounced / emails_sent * 100) if emails_sent > 0 else 0
    delivery_rate = (emails_delivered / emails_sent * 100) if emails_sent > 0 else 0

    # Get engagement timeline (last 7 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)

    timeline_events = (
        events.filter(timestamp__gte=start_date)
        .values("timestamp__date", "event_type")
        .annotate(count=Count("id"))
        .order_by("timestamp__date")
    )

    # Get top performing links
    top_links = (
        events.filter(event_type=EmailEvent.EventType.CLICKED)
        .values("url")
        .annotate(click_count=Count("id"))
        .order_by("-click_count")[:10]
    )

    # Get device breakdown
    device_breakdown = (
        events.filter(
            event_type__in=[EmailEvent.EventType.OPENED, EmailEvent.EventType.CLICKED]
        )
        .values("device_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Get location breakdown
    location_breakdown = (
        events.filter(
            event_type__in=[EmailEvent.EventType.OPENED, EmailEvent.EventType.CLICKED]
        )
        .values("country")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "total_recipients": total_recipients,
        "emails_sent": emails_sent,
        "emails_delivered": emails_delivered,
        "emails_bounced": emails_bounced,
        "emails_opened": emails_opened,
        "emails_clicked": emails_clicked,
        "unsubscribes": unsubscribes,
        "complaints": complaints,
        "open_rate": round(open_rate, 2),
        "click_rate": round(click_rate, 2),
        "bounce_rate": round(bounce_rate, 2),
        "delivery_rate": round(delivery_rate, 2),
        "engagement_timeline": list(timeline_events),
        "top_links": list(top_links),
        "device_breakdown": list(device_breakdown),
        "location_breakdown": list(location_breakdown),
    }


def get_campaign_performance_comparison(campaigns):
    """
    Compare performance across multiple campaigns.
    """
    comparison_data = []

    for campaign in campaigns:
        metrics = calculate_engagement_metrics(campaign)
        comparison_data.append(
            {
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "open_rate": metrics["open_rate"],
                "click_rate": metrics["click_rate"],
                "bounce_rate": metrics["bounce_rate"],
                "delivery_rate": metrics["delivery_rate"],
                "emails_sent": metrics["emails_sent"],
            }
        )

    return comparison_data


def get_campaign_trends(user, days=30):
    """
    Get campaign performance trends over time.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Get daily reports
    daily_reports = CampaignReport.objects.filter(
        campaign__in=campaigns, date__gte=start_date
    ).order_by("date")

    # Aggregate by date
    trends = {}
    for report in daily_reports:
        date_str = report.date.isoformat()
        if date_str not in trends:
            trends[date_str] = {
                "date": date_str,
                "emails_sent": 0,
                "emails_delivered": 0,
                "emails_opened": 0,
                "emails_clicked": 0,
                "unsubscribes": 0,
                "complaints": 0,
            }

        trends[date_str]["emails_sent"] += report.emails_sent
        trends[date_str]["emails_delivered"] += report.emails_delivered
        trends[date_str]["emails_opened"] += report.unique_opens
        trends[date_str]["emails_clicked"] += report.unique_clicks
        trends[date_str]["unsubscribes"] += report.unsubscribes
        trends[date_str]["complaints"] += report.complaints

    # Calculate rates for each day
    for date_str, data in trends.items():
        if data["emails_delivered"] > 0:
            data["open_rate"] = (data["emails_opened"] / data["emails_delivered"]) * 100
            data["click_rate"] = (
                data["emails_clicked"] / data["emails_delivered"]
            ) * 100
        else:
            data["open_rate"] = 0
            data["click_rate"] = 0

        if data["emails_sent"] > 0:
            data["delivery_rate"] = (
                data["emails_delivered"] / data["emails_sent"]
            ) * 100
        else:
            data["delivery_rate"] = 0

    return list(trends.values())


def get_top_performing_campaigns(user, limit=10):
    """
    Get top performing campaigns by open rate.
    """
    if user.is_admin:
        campaigns = Campaign.objects.filter(emails_delivered__gt=0).order_by(
            "-emails_opened"
        )[:limit]
    else:
        campaigns = (
            Campaign.objects.filter(
                Q(team__members=user) | Q(created_by=user), emails_delivered__gt=0
            )
            .distinct()
            .order_by("-emails_opened")[:limit]
        )

    return campaigns


def get_campaign_health_score(campaign):
    """
    Calculate a health score for a campaign based on various metrics.
    """
    score = 0
    max_score = 100

    # Delivery rate (30 points)
    if campaign.emails_sent > 0:
        delivery_rate = (campaign.emails_delivered / campaign.emails_sent) * 100
        score += min(delivery_rate * 0.3, 30)

    # Open rate (25 points)
    if campaign.emails_delivered > 0:
        open_rate = (campaign.emails_opened / campaign.emails_delivered) * 100
        score += min(open_rate * 0.25, 25)

    # Click rate (20 points)
    if campaign.emails_delivered > 0:
        click_rate = (campaign.emails_clicked / campaign.emails_delivered) * 100
        score += min(click_rate * 0.2, 20)

    # Low bounce rate (15 points)
    if campaign.emails_sent > 0:
        bounce_rate = (campaign.emails_bounced / campaign.emails_sent) * 100
        score += max(15 - bounce_rate, 0)

    # Low complaint rate (10 points)
    if campaign.emails_delivered > 0:
        complaint_rate = (campaign.complaints / campaign.emails_delivered) * 100
        score += max(10 - complaint_rate * 10, 0)

    return min(round(score), max_score)


def validate_campaign_before_sending(campaign):
    """
    Validate a campaign before sending to ensure it's ready.
    """
    errors = []

    # Check required fields
    if not campaign.subject or not campaign.subject.strip():
        errors.append("Subject is required")

    if not campaign.html_content or not campaign.html_content.strip():
        errors.append("HTML content is required")

    if not campaign.from_email or not campaign.from_email.strip():
        errors.append("From email is required")

    if not campaign.from_name or not campaign.from_name.strip():
        errors.append("From name is required")

    # Check subscriber lists
    if not campaign.subscriber_lists.exists():
        errors.append("At least one subscriber list is required")

    # Check if campaign can be sent
    if not campaign.can_send():
        errors.append(f"Campaign cannot be sent in current status: {campaign.status}")

    # Check if scheduled time is valid
    if campaign.send_at and campaign.send_at <= timezone.now():
        errors.append("Scheduled time must be in the future")

    return errors
