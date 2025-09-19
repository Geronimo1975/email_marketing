from django.db.models import Q, Count, Sum, Avg, F, Max, Min
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from .models import (
    EmailEvent,
    CampaignReport,
    SubscriberActivity,
    LinkClick,
    DomainReputation,
)

User = get_user_model()


def get_dashboard_stats(user, date_from, date_to):
    """
    Get comprehensive dashboard statistics for a user.
    """
    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        from apps.campaigns.models import Campaign

        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by date range
    campaigns = campaigns.filter(created_at__date__range=[date_from, date_to])

    # Get email events for these campaigns
    events = EmailEvent.objects.filter(
        campaign__in=campaigns, timestamp__date__range=[date_from, date_to]
    )

    # Basic metrics
    total_campaigns = campaigns.count()
    total_emails_sent = campaigns.aggregate(total=Sum("emails_sent"))["total"] or 0

    total_emails_delivered = (
        campaigns.aggregate(total=Sum("emails_delivered"))["total"] or 0
    )

    total_emails_opened = events.filter(event_type=EmailEvent.EventType.OPENED).count()

    total_emails_clicked = events.filter(
        event_type=EmailEvent.EventType.CLICKED
    ).count()

    total_emails_bounced = events.filter(
        event_type=EmailEvent.EventType.BOUNCED
    ).count()

    total_unsubscribes = events.filter(
        event_type=EmailEvent.EventType.UNSUBSCRIBED
    ).count()

    # Get subscriber count
    from apps.subscribers.models import Subscriber

    if user.is_admin:
        total_subscribers = Subscriber.objects.count()
    else:
        total_subscribers = (
            Subscriber.objects.filter(Q(team__members=user) | Q(team__isnull=True))
            .distinct()
            .count()
        )

    # Calculate rates
    open_rate = (
        (total_emails_opened / total_emails_delivered * 100)
        if total_emails_delivered > 0
        else 0
    )
    click_rate = (
        (total_emails_clicked / total_emails_delivered * 100)
        if total_emails_delivered > 0
        else 0
    )
    bounce_rate = (
        (total_emails_bounced / total_emails_sent * 100) if total_emails_sent > 0 else 0
    )
    delivery_rate = (
        (total_emails_delivered / total_emails_sent * 100)
        if total_emails_sent > 0
        else 0
    )

    # Growth metrics (compared to previous period)
    prev_date_from = date_from - (date_to - date_from)
    prev_date_to = date_from - timedelta(days=1)

    prev_events = EmailEvent.objects.filter(
        campaign__in=campaigns, timestamp__date__range=[prev_date_from, prev_date_to]
    )

    prev_emails_sent = (
        campaigns.filter(
            created_at__date__range=[prev_date_from, prev_date_to]
        ).aggregate(total=Sum("emails_sent"))["total"]
        or 0
    )

    subscriber_growth = 0
    if prev_emails_sent > 0:
        current_emails = total_emails_sent
        subscriber_growth = (current_emails - prev_emails_sent) / prev_emails_sent * 100

    return {
        "total_campaigns": total_campaigns,
        "total_emails_sent": total_emails_sent,
        "total_emails_delivered": total_emails_delivered,
        "total_emails_opened": total_emails_opened,
        "total_emails_clicked": total_emails_clicked,
        "total_emails_bounced": total_emails_bounced,
        "total_unsubscribes": total_unsubscribes,
        "total_subscribers": total_subscribers,
        "open_rate": round(open_rate, 2),
        "click_rate": round(click_rate, 2),
        "bounce_rate": round(bounce_rate, 2),
        "delivery_rate": round(delivery_rate, 2),
        "subscriber_growth": round(subscriber_growth, 2),
        "engagement_growth": 0,  # Will be calculated separately
    }


def get_campaign_performance(user, date_from, date_to, campaign_id=None):
    """
    Get campaign performance metrics.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by date range
    campaigns = campaigns.filter(created_at__date__range=[date_from, date_to])

    # Filter by specific campaign if provided
    if campaign_id:
        campaigns = campaigns.filter(id=campaign_id)

    performance_data = []

    for campaign in campaigns:
        # Get events for this campaign
        events = EmailEvent.objects.filter(
            campaign=campaign, timestamp__date__range=[date_from, date_to]
        )

        # Calculate metrics
        emails_opened = events.filter(event_type=EmailEvent.EventType.OPENED).count()

        emails_clicked = events.filter(event_type=EmailEvent.EventType.CLICKED).count()

        emails_bounced = events.filter(event_type=EmailEvent.EventType.BOUNCED).count()

        unsubscribes = events.filter(
            event_type=EmailEvent.EventType.UNSUBSCRIBED
        ).count()

        # Calculate rates
        open_rate = (
            (emails_opened / campaign.emails_delivered * 100)
            if campaign.emails_delivered > 0
            else 0
        )
        click_rate = (
            (emails_clicked / campaign.emails_delivered * 100)
            if campaign.emails_delivered > 0
            else 0
        )
        bounce_rate = (
            (emails_bounced / campaign.emails_sent * 100)
            if campaign.emails_sent > 0
            else 0
        )
        delivery_rate = (
            (campaign.emails_delivered / campaign.emails_sent * 100)
            if campaign.emails_sent > 0
            else 0
        )

        performance_data.append(
            {
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "subject": campaign.subject,
                "status": campaign.status,
                "emails_sent": campaign.emails_sent,
                "emails_delivered": campaign.emails_delivered,
                "emails_opened": emails_opened,
                "emails_clicked": emails_clicked,
                "emails_bounced": emails_bounced,
                "unsubscribes": unsubscribes,
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "delivery_rate": round(delivery_rate, 2),
                "created_at": campaign.created_at,
                "sent_at": campaign.sent_at,
            }
        )

    return performance_data


def get_subscriber_engagement(user, date_from, date_to):
    """
    Get subscriber engagement metrics.
    """
    from apps.subscribers.models import Subscriber

    # Get user's subscribers
    if user.is_admin:
        subscribers = Subscriber.objects.all()
    else:
        subscribers = Subscriber.objects.filter(
            Q(team__members=user) | Q(team__isnull=True)
        ).distinct()

    # Get subscriber activity
    activity = SubscriberActivity.objects.filter(
        subscriber__in=subscribers, date__range=[date_from, date_to]
    )

    # Calculate metrics
    total_subscribers = subscribers.count()
    active_subscribers = subscribers.filter(status=Subscriber.Status.SUBSCRIBED).count()

    engaged_subscribers = subscribers.filter(engagement_score__gte=50).count()

    inactive_subscribers = subscribers.filter(
        last_activity__lt=timezone.now() - timedelta(days=30)
    ).count()

    # Calculate rates
    engagement_rate = (
        (engaged_subscribers / total_subscribers * 100) if total_subscribers > 0 else 0
    )
    activity_rate = (
        (active_subscribers / total_subscribers * 100) if total_subscribers > 0 else 0
    )

    # Growth metrics
    new_subscribers = subscribers.filter(
        created_at__date__range=[date_from, date_to]
    ).count()

    unsubscribed_subscribers = subscribers.filter(
        status=Subscriber.Status.UNSUBSCRIBED,
        updated_at__date__range=[date_from, date_to],
    ).count()

    bounced_subscribers = subscribers.filter(
        status=Subscriber.Status.BOUNCED, updated_at__date__range=[date_from, date_to]
    ).count()

    return {
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "engaged_subscribers": engaged_subscribers,
        "inactive_subscribers": inactive_subscribers,
        "engagement_rate": round(engagement_rate, 2),
        "activity_rate": round(activity_rate, 2),
        "new_subscribers": new_subscribers,
        "unsubscribed_subscribers": unsubscribed_subscribers,
        "bounced_subscribers": bounced_subscribers,
    }


def get_email_metrics(user, date_from, date_to):
    """
    Get email volume and performance metrics.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by date range
    campaigns = campaigns.filter(created_at__date__range=[date_from, date_to])

    # Volume metrics
    total_emails = campaigns.aggregate(total=Sum("emails_sent"))["total"] or 0

    today = timezone.now().date()
    emails_sent_today = (
        campaigns.filter(sent_at__date=today).aggregate(total=Sum("emails_sent"))[
            "total"
        ]
        or 0
    )

    week_start = today - timedelta(days=today.weekday())
    emails_sent_this_week = (
        campaigns.filter(sent_at__date__gte=week_start).aggregate(
            total=Sum("emails_sent")
        )["total"]
        or 0
    )

    month_start = today.replace(day=1)
    emails_sent_this_month = (
        campaigns.filter(sent_at__date__gte=month_start).aggregate(
            total=Sum("emails_sent")
        )["total"]
        or 0
    )

    # Performance metrics
    total_delivered = campaigns.aggregate(total=Sum("emails_delivered"))["total"] or 0
    total_opened = campaigns.aggregate(total=Sum("emails_opened"))["total"] or 0
    total_clicked = campaigns.aggregate(total=Sum("emails_clicked"))["total"] or 0
    total_bounced = campaigns.aggregate(total=Sum("emails_bounced"))["total"] or 0

    average_open_rate = (
        (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    )
    average_click_rate = (
        (total_clicked / total_delivered * 100) if total_delivered > 0 else 0
    )
    average_bounce_rate = (
        (total_bounced / total_emails * 100) if total_emails > 0 else 0
    )
    average_delivery_rate = (
        (total_delivered / total_emails * 100) if total_emails > 0 else 0
    )

    return {
        "total_emails": total_emails,
        "emails_sent_today": emails_sent_today,
        "emails_sent_this_week": emails_sent_this_week,
        "emails_sent_this_month": emails_sent_this_month,
        "average_open_rate": round(average_open_rate, 2),
        "average_click_rate": round(average_click_rate, 2),
        "average_bounce_rate": round(average_bounce_rate, 2),
        "average_delivery_rate": round(average_delivery_rate, 2),
    }


def get_click_analytics(campaign, date_from, date_to):
    """
    Get click analytics for a campaign.
    """
    # Get click events
    click_events = EmailEvent.objects.filter(
        campaign=campaign,
        event_type=EmailEvent.EventType.CLICKED,
        timestamp__date__range=[date_from, date_to],
    )

    # Basic metrics
    total_clicks = click_events.count()
    unique_clicks = click_events.values("recipient_email").distinct().count()
    click_through_rate = (
        (unique_clicks / campaign.emails_delivered * 100)
        if campaign.emails_delivered > 0
        else 0
    )

    # Top links
    top_links = (
        click_events.values("url")
        .annotate(
            click_count=Count("id"),
            unique_clicks=Count("recipient_email", distinct=True),
        )
        .order_by("-click_count")[:10]
    )

    # Device breakdown
    device_breakdown = (
        click_events.values("device_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Location breakdown
    location_breakdown = (
        click_events.values("country")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    return {
        "total_clicks": total_clicks,
        "unique_clicks": unique_clicks,
        "click_through_rate": round(click_through_rate, 2),
        "top_links": list(top_links),
        "device_breakdown": list(device_breakdown),
        "location_breakdown": list(location_breakdown),
    }


def get_delivery_analytics(campaign, date_from, date_to):
    """
    Get delivery analytics for a campaign.
    """
    # Get delivery events
    delivery_events = EmailEvent.objects.filter(
        campaign=campaign,
        event_type=EmailEvent.EventType.DELIVERED,
        timestamp__date__range=[date_from, date_to],
    )

    bounce_events = EmailEvent.objects.filter(
        campaign=campaign,
        event_type=EmailEvent.EventType.BOUNCED,
        timestamp__date__range=[date_from, date_to],
    )

    # Basic metrics
    total_sent = campaign.emails_sent
    total_delivered = delivery_events.count()
    total_bounced = bounce_events.count()
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
    bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0

    # Bounce breakdown
    bounce_breakdown = (
        bounce_events.values("bounce_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_bounced": total_bounced,
        "delivery_rate": round(delivery_rate, 2),
        "bounce_rate": round(bounce_rate, 2),
        "bounce_breakdown": list(bounce_breakdown),
    }


def get_engagement_timeline(user, date_from, date_to, campaign_id=None):
    """
    Get engagement timeline data.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by specific campaign if provided
    if campaign_id:
        campaigns = campaigns.filter(id=campaign_id)

    # Get events
    events = EmailEvent.objects.filter(
        campaign__in=campaigns, timestamp__date__range=[date_from, date_to]
    )

    # Group by date
    timeline_data = (
        events.extra(select={"date": "DATE(timestamp)"})
        .values("date")
        .annotate(
            opens=Count("id", filter=Q(event_type=EmailEvent.EventType.OPENED)),
            clicks=Count("id", filter=Q(event_type=EmailEvent.EventType.CLICKED)),
            bounces=Count("id", filter=Q(event_type=EmailEvent.EventType.BOUNCED)),
            unsubscribes=Count(
                "id", filter=Q(event_type=EmailEvent.EventType.UNSUBSCRIBED)
            ),
        )
        .order_by("date")
    )

    return list(timeline_data)


def get_top_performing_campaigns(user, date_from, date_to, limit=10):
    """
    Get top performing campaigns by engagement.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by date range
    campaigns = campaigns.filter(created_at__date__range=[date_from, date_to])

    # Calculate engagement score for each campaign
    top_campaigns = []
    for campaign in campaigns:
        if campaign.emails_delivered > 0:
            engagement_score = campaign.open_rate * 0.4 + campaign.click_rate * 0.6

            top_campaigns.append(
                {
                    "campaign_id": campaign.id,
                    "campaign_name": campaign.name,
                    "subject": campaign.subject,
                    "emails_sent": campaign.emails_sent,
                    "open_rate": campaign.open_rate,
                    "click_rate": campaign.click_rate,
                    "engagement_score": round(engagement_score, 2),
                    "created_at": campaign.created_at,
                }
            )

    # Sort by engagement score
    top_campaigns.sort(key=lambda x: x["engagement_score"], reverse=True)

    return top_campaigns[:limit]


def get_device_breakdown(user, date_from, date_to, campaign_id=None):
    """
    Get device breakdown for events.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by specific campaign if provided
    if campaign_id:
        campaigns = campaigns.filter(id=campaign_id)

    # Get events
    events = EmailEvent.objects.filter(
        campaign__in=campaigns, timestamp__date__range=[date_from, date_to]
    )

    # Device breakdown
    device_breakdown = (
        events.values("device_type").annotate(count=Count("id")).order_by("-count")
    )

    total_events = events.count()

    # Calculate percentages
    device_data = []
    for device in device_breakdown:
        percentage = (device["count"] / total_events * 100) if total_events > 0 else 0
        device_data.append(
            {
                "device_type": device["device_type"] or "Unknown",
                "count": device["count"],
                "percentage": round(percentage, 2),
            }
        )

    return device_data


def get_location_breakdown(user, date_from, date_to, campaign_id=None):
    """
    Get location breakdown for events.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Filter by specific campaign if provided
    if campaign_id:
        campaigns = campaigns.filter(id=campaign_id)

    # Get events
    events = EmailEvent.objects.filter(
        campaign__in=campaigns, timestamp__date__range=[date_from, date_to]
    )

    # Country breakdown
    country_breakdown = (
        events.values("country").annotate(count=Count("id")).order_by("-count")[:10]
    )

    # City breakdown
    city_breakdown = (
        events.values("city").annotate(count=Count("id")).order_by("-count")[:10]
    )

    return {
        "countries": list(country_breakdown),
        "cities": list(city_breakdown),
    }


def get_unsubscribe_analytics(user, date_from, date_to):
    """
    Get unsubscribe analytics.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Get unsubscribe events
    unsubscribe_events = EmailEvent.objects.filter(
        campaign__in=campaigns,
        event_type=EmailEvent.EventType.UNSUBSCRIBED,
        timestamp__date__range=[date_from, date_to],
    )

    # Basic metrics
    total_unsubscribes = unsubscribe_events.count()

    # Calculate unsubscribe rate
    total_delivered = (
        campaigns.filter(created_at__date__range=[date_from, date_to]).aggregate(
            total=Sum("emails_delivered")
        )["total"]
        or 0
    )

    unsubscribe_rate = (
        (total_unsubscribes / total_delivered * 100) if total_delivered > 0 else 0
    )

    # Unsubscribe trend by date
    unsubscribe_trend = (
        unsubscribe_events.extra(select={"date": "DATE(timestamp)"})
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    return {
        "total_unsubscribes": total_unsubscribes,
        "unsubscribe_rate": round(unsubscribe_rate, 2),
        "unsubscribe_trend": list(unsubscribe_trend),
    }


def get_bounce_analytics(user, date_from, date_to):
    """
    Get bounce analytics.
    """
    from apps.campaigns.models import Campaign

    # Get user's campaigns
    if user.is_admin:
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Get bounce events
    bounce_events = EmailEvent.objects.filter(
        campaign__in=campaigns,
        event_type=EmailEvent.EventType.BOUNCED,
        timestamp__date__range=[date_from, date_to],
    )

    # Basic metrics
    total_bounces = bounce_events.count()

    # Calculate bounce rate
    total_sent = (
        campaigns.filter(created_at__date__range=[date_from, date_to]).aggregate(
            total=Sum("emails_sent")
        )["total"]
        or 0
    )

    bounce_rate = (total_bounces / total_sent * 100) if total_sent > 0 else 0

    # Bounce types
    bounce_types = (
        bounce_events.values("bounce_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Bounce trend by date
    bounce_trend = (
        bounce_events.extra(select={"date": "DATE(timestamp)"})
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    return {
        "total_bounces": total_bounces,
        "bounce_rate": round(bounce_rate, 2),
        "bounce_types": list(bounce_types),
        "bounce_trend": list(bounce_trend),
    }
