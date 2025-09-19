from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Campaign, EmailTemplate, CampaignRecipient, CampaignVariant
from apps.subscribers.models import SubscriberList, Tag

User = get_user_model()


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for EmailTemplate model"""

    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "name",
            "description",
            "type",
            "subject",
            "html_content",
            "text_content",
            "variables",
            "thumbnail",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CampaignVariantSerializer(serializers.ModelSerializer):
    """Serializer for CampaignVariant model"""

    class Meta:
        model = CampaignVariant
        fields = [
            "id",
            "name",
            "subject",
            "html_content",
            "text_content",
            "percentage",
            "emails_sent",
            "emails_opened",
            "emails_clicked",
            "is_winner",
            "open_rate",
            "click_rate",
        ]
        read_only_fields = [
            "emails_sent",
            "emails_opened",
            "emails_clicked",
            "is_winner",
        ]


class CampaignRecipientSerializer(serializers.ModelSerializer):
    """Serializer for CampaignRecipient model"""

    subscriber_email = serializers.CharField(source="subscriber.email", read_only=True)
    subscriber_name = serializers.CharField(
        source="subscriber.full_name", read_only=True
    )

    class Meta:
        model = CampaignRecipient
        fields = [
            "id",
            "subscriber",
            "subscriber_email",
            "subscriber_name",
            "status",
            "mailgun_message_id",
            "personalized_subject",
            "personalized_content",
            "sent_at",
            "delivered_at",
            "bounced_at",
            "bounce_reason",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class CampaignListSerializer(serializers.ModelSerializer):
    """Simplified serializer for campaign lists"""

    created_by_name = serializers.CharField(source="created_by.email", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "description",
            "type",
            "status",
            "subject",
            "from_email",
            "from_name",
            "total_recipients",
            "emails_sent",
            "emails_delivered",
            "emails_opened",
            "emails_clicked",
            "unsubscribes",
            "complaints",
            "open_rate",
            "click_rate",
            "bounce_rate",
            "created_by_name",
            "team_name",
            "subscriber_count",
            "send_at",
            "created_at",
            "sent_at",
        ]
        read_only_fields = ["created_at", "sent_at"]

    def get_subscriber_count(self, obj):
        from django.db.models import Count

        return obj.subscriber_lists.aggregate(total=Count("subscribers"))["total"] or 0


class CampaignSerializer(serializers.ModelSerializer):
    """Full serializer for Campaign model"""

    created_by_name = serializers.CharField(source="created_by.email", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    subscriber_lists = serializers.PrimaryKeyRelatedField(
        queryset=SubscriberList.objects.all(), many=True, required=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )
    variants = CampaignVariantSerializer(many=True, read_only=True)
    recipients = CampaignRecipientSerializer(many=True, read_only=True)

    # Computed fields
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    bounce_rate = serializers.ReadOnlyField()
    delivery_rate = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "description",
            "type",
            "status",
            "subject",
            "from_email",
            "from_name",
            "reply_to",
            "template",
            "template_name",
            "html_content",
            "text_content",
            "subscriber_lists",
            "tags",
            "send_at",
            "timezone",
            "ab_test_percentage",
            "ab_winner_criteria",
            "ab_test_duration",
            "track_opens",
            "track_clicks",
            "total_recipients",
            "emails_sent",
            "emails_delivered",
            "emails_bounced",
            "emails_opened",
            "emails_clicked",
            "unsubscribes",
            "complaints",
            "open_rate",
            "click_rate",
            "bounce_rate",
            "delivery_rate",
            "created_by",
            "created_by_name",
            "team",
            "team_name",
            "variants",
            "recipients",
            "created_at",
            "updated_at",
            "sent_at",
        ]
        read_only_fields = ["created_at", "updated_at", "sent_at"]

    def get_delivery_rate(self, obj):
        if obj.emails_sent > 0:
            return (obj.emails_delivered / obj.emails_sent) * 100
        return 0

    def create(self, validated_data):
        # Extract many-to-many fields
        subscriber_lists = validated_data.pop("subscriber_lists", [])
        tags = validated_data.pop("tags", [])

        # Create campaign
        campaign = Campaign.objects.create(**validated_data)

        # Set many-to-many relationships
        campaign.subscriber_lists.set(subscriber_lists)
        campaign.tags.set(tags)

        return campaign

    def update(self, instance, validated_data):
        # Extract many-to-many fields
        subscriber_lists = validated_data.pop("subscriber_lists", None)
        tags = validated_data.pop("tags", None)

        # Update campaign
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update many-to-many relationships if provided
        if subscriber_lists is not None:
            instance.subscriber_lists.set(subscriber_lists)
        if tags is not None:
            instance.tags.set(tags)

        return instance


class CampaignCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating campaigns with validation"""

    subscriber_lists = serializers.PrimaryKeyRelatedField(
        queryset=SubscriberList.objects.all(), many=True, required=True
    )

    class Meta:
        model = Campaign
        fields = [
            "name",
            "description",
            "type",
            "subject",
            "from_email",
            "from_name",
            "reply_to",
            "template",
            "html_content",
            "text_content",
            "subscriber_lists",
            "tags",
            "send_at",
            "timezone",
            "track_opens",
            "track_clicks",
        ]

    def validate_subject(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Subject cannot be empty")
        return value.strip()

    def validate_html_content(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("HTML content cannot be empty")
        return value

    def validate_subscriber_lists(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one subscriber list is required"
            )
        return value

    def validate_send_at(self, value):
        from django.utils import timezone

        if value and value <= timezone.now():
            raise serializers.ValidationError("Send time must be in the future")
        return value


class CampaignStatsSerializer(serializers.Serializer):
    """Serializer for campaign statistics"""

    campaign_id = serializers.IntegerField()
    campaign_name = serializers.CharField()

    # Basic metrics
    total_recipients = serializers.IntegerField()
    emails_sent = serializers.IntegerField()
    emails_delivered = serializers.IntegerField()
    emails_bounced = serializers.IntegerField()
    emails_opened = serializers.IntegerField()
    emails_clicked = serializers.IntegerField()
    unsubscribes = serializers.IntegerField()
    complaints = serializers.IntegerField()

    # Calculated rates
    open_rate = serializers.FloatField()
    click_rate = serializers.FloatField()
    bounce_rate = serializers.FloatField()
    delivery_rate = serializers.FloatField()

    # Timeline data
    engagement_timeline = serializers.ListField(child=serializers.DictField())

    # Top performing content
    top_links = serializers.ListField(child=serializers.DictField())
    device_breakdown = serializers.DictField()
    location_breakdown = serializers.DictField()


class CampaignActionSerializer(serializers.Serializer):
    """Serializer for campaign actions"""

    action = serializers.ChoiceField(
        choices=["send", "schedule", "pause", "resume", "cancel", "duplicate"]
    )
    send_at = serializers.DateTimeField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
