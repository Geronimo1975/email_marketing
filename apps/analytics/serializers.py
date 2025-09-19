from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    EmailEvent,
    CampaignReport,
    SubscriberActivity,
    LinkClick,
    DomainReputation,
)

User = get_user_model()


class EmailEventSerializer(serializers.ModelSerializer):
    """Serializer for EmailEvent model"""

    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )

    class Meta:
        model = EmailEvent
        fields = [
            "id",
            "campaign",
            "campaign_name",
            "recipient_email",
            "event_type",
            "event_type_display",
            "timestamp",
            "url",
            "user_agent",
            "ip_address",
            "device_type",
            "country",
            "city",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class CampaignReportSerializer(serializers.ModelSerializer):
    """Serializer for CampaignReport model"""

    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = CampaignReport
        fields = [
            "id",
            "campaign",
            "campaign_name",
            "date",
            "emails_sent",
            "emails_delivered",
            "emails_bounced",
            "emails_opened",
            "emails_clicked",
            "unique_opens",
            "unique_clicks",
            "unsubscribes",
            "complaints",
            "open_rate",
            "click_rate",
            "bounce_rate",
            "delivery_rate",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SubscriberActivitySerializer(serializers.ModelSerializer):
    """Serializer for SubscriberActivity model"""

    subscriber_email = serializers.CharField(source="subscriber.email", read_only=True)

    class Meta:
        model = SubscriberActivity
        fields = [
            "id",
            "subscriber",
            "subscriber_email",
            "date",
            "opens",
            "clicks",
            "bounces",
            "unsubscribes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class LinkClickSerializer(serializers.ModelSerializer):
    """Serializer for LinkClick model"""

    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = LinkClick
        fields = [
            "id",
            "campaign",
            "campaign_name",
            "url",
            "click_count",
            "unique_clicks",
            "last_clicked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class DomainReputationSerializer(serializers.ModelSerializer):
    """Serializer for DomainReputation model"""

    class Meta:
        model = DomainReputation
        fields = [
            "id",
            "domain",
            "reputation_score",
            "delivery_rate",
            "bounce_rate",
            "complaint_rate",
            "last_checked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AnalyticsDashboardSerializer(serializers.Serializer):
    """Serializer for analytics dashboard data"""

    # Basic metrics
    total_campaigns = serializers.IntegerField()
    total_emails_sent = serializers.IntegerField()
    total_emails_delivered = serializers.IntegerField()
    total_emails_opened = serializers.IntegerField()
    total_emails_clicked = serializers.IntegerField()
    total_subscribers = serializers.IntegerField()

    # Rates
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()
    bounce_rate = serializers.FloatField()
    delivery_rate = serializers.FloatField()

    # Growth metrics
    subscriber_growth = serializers.FloatField()
    engagement_growth = serializers.FloatField()

    # Timeline data
    engagement_timeline = serializers.ListField(child=serializers.DictField())

    # Top performing data
    top_campaigns = serializers.ListField(child=serializers.DictField())
    top_links = serializers.ListField(child=serializers.DictField())

    # Device and location breakdown
    device_breakdown = serializers.ListField(child=serializers.DictField())
    location_breakdown = serializers.ListField(child=serializers.DictField())


class CampaignPerformanceSerializer(serializers.Serializer):
    """Serializer for campaign performance data"""

    campaign_id = serializers.IntegerField()
    campaign_name = serializers.CharField()
    subject = serializers.CharField()
    status = serializers.CharField()

    # Metrics
    emails_sent = serializers.IntegerField()
    emails_delivered = serializers.IntegerField()
    emails_opened = serializers.IntegerField()
    emails_clicked = serializers.IntegerField()
    emails_bounced = serializers.IntegerField()
    unsubscribes = serializers.IntegerField()
    complaints = serializers.IntegerField()

    # Rates
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()
    bounce_rate = serializers.FloatField()
    delivery_rate = serializers.FloatField()

    # Dates
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)


class SubscriberEngagementSerializer(serializers.Serializer):
    """Serializer for subscriber engagement data"""

    # Engagement metrics
    total_subscribers = serializers.IntegerField()
    active_subscribers = serializers.IntegerField()
    engaged_subscribers = serializers.IntegerField()
    inactive_subscribers = serializers.IntegerField()

    # Engagement rates
    engagement_rate = serializers.FloatField()
    activity_rate = serializers.FloatField()

    # Growth metrics
    new_subscribers = serializers.IntegerField()
    unsubscribed_subscribers = serializers.IntegerField()
    bounced_subscribers = serializers.IntegerField()

    # Timeline data
    engagement_timeline = serializers.ListField(child=serializers.DictField())

    # Top engaged subscribers
    top_engaged = serializers.ListField(child=serializers.DictField())


class EmailMetricsSerializer(serializers.Serializer):
    """Serializer for email metrics data"""

    # Volume metrics
    total_emails = serializers.IntegerField()
    emails_sent_today = serializers.IntegerField()
    emails_sent_this_week = serializers.IntegerField()
    emails_sent_this_month = serializers.IntegerField()

    # Performance metrics
    average_open_rate = serializers.FloatField()
    average_click_rate = serializers.FloatField()
    average_bounce_rate = serializers.FloatField()
    average_delivery_rate = serializers.FloatField()

    # Trend data
    daily_volume = serializers.ListField(child=serializers.DictField())
    performance_trends = serializers.ListField(child=serializers.DictField())


class ClickAnalyticsSerializer(serializers.Serializer):
    """Serializer for click analytics data"""

    # Click metrics
    total_clicks = serializers.IntegerField()
    unique_clicks = serializers.IntegerField()
    click_through_rate = serializers.FloatField()

    # Top links
    top_links = serializers.ListField(child=serializers.DictField())

    # Click timeline
    click_timeline = serializers.ListField(child=serializers.DictField())

    # Device breakdown
    device_breakdown = serializers.ListField(child=serializers.DictField())

    # Location breakdown
    location_breakdown = serializers.ListField(child=serializers.DictField())


class DeliveryAnalyticsSerializer(serializers.Serializer):
    """Serializer for delivery analytics data"""

    # Delivery metrics
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_bounced = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    bounce_rate = serializers.FloatField()

    # Bounce breakdown
    bounce_breakdown = serializers.ListField(child=serializers.DictField())

    # Delivery timeline
    delivery_timeline = serializers.ListField(child=serializers.DictField())

    # Domain reputation
    domain_reputation = serializers.ListField(child=serializers.DictField())


class EngagementTimelineSerializer(serializers.Serializer):
    """Serializer for engagement timeline data"""

    # Timeline data
    timeline = serializers.ListField(child=serializers.DictField())

    # Summary metrics
    total_opens = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    peak_engagement_day = serializers.CharField()
    peak_engagement_time = serializers.CharField()


class DeviceBreakdownSerializer(serializers.Serializer):
    """Serializer for device breakdown data"""

    # Device metrics
    desktop_clicks = serializers.IntegerField()
    mobile_clicks = serializers.IntegerField()
    tablet_clicks = serializers.IntegerField()

    # Device percentages
    desktop_percentage = serializers.FloatField()
    mobile_percentage = serializers.FloatField()
    tablet_percentage = serializers.FloatField()

    # Device details
    device_details = serializers.ListField(child=serializers.DictField())


class LocationBreakdownSerializer(serializers.Serializer):
    """Serializer for location breakdown data"""

    # Location metrics
    total_countries = serializers.IntegerField()
    total_cities = serializers.IntegerField()

    # Top locations
    top_countries = serializers.ListField(child=serializers.DictField())
    top_cities = serializers.ListField(child=serializers.DictField())

    # Geographic distribution
    geographic_data = serializers.ListField(child=serializers.DictField())


class UnsubscribeAnalyticsSerializer(serializers.Serializer):
    """Serializer for unsubscribe analytics data"""

    # Unsubscribe metrics
    total_unsubscribes = serializers.IntegerField()
    unsubscribe_rate = serializers.FloatField()
    unsubscribe_trend = serializers.ListField(child=serializers.DictField())

    # Reasons breakdown
    unsubscribe_reasons = serializers.ListField(child=serializers.DictField())

    # Campaign impact
    campaign_impact = serializers.ListField(child=serializers.DictField())


class BounceAnalyticsSerializer(serializers.Serializer):
    """Serializer for bounce analytics data"""

    # Bounce metrics
    total_bounces = serializers.IntegerField()
    bounce_rate = serializers.FloatField()
    bounce_trend = serializers.ListField(child=serializers.DictField())

    # Bounce types
    hard_bounces = serializers.IntegerField()
    soft_bounces = serializers.IntegerField()
    bounce_types = serializers.ListField(child=serializers.DictField())

    # Domain analysis
    domain_analysis = serializers.ListField(child=serializers.DictField())
