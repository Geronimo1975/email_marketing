from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subscriber, SubscriberList, Tag, SegmentRule, Subscription

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "description",
            "color",
            "team",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SubscriberListSerializer(serializers.ModelSerializer):
    """Serializer for SubscriberList model"""

    team_name = serializers.CharField(source="team.name", read_only=True)
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriberList
        fields = [
            "id",
            "name",
            "description",
            "team",
            "team_name",
            "subscriber_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_subscriber_count(self, obj):
        from django.db.models import Count

        return obj.subscribers.aggregate(total=Count("id"))["total"] or 0


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model"""

    subscriber_email = serializers.CharField(source="subscriber.email", read_only=True)
    list_name = serializers.CharField(source="subscriber_list.name", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "subscriber",
            "subscriber_email",
            "subscriber_list",
            "list_name",
            "subscribed_at",
            "unsubscribed_at",
            "status",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class SubscriberSerializer(serializers.ModelSerializer):
    """Full serializer for Subscriber model"""

    team_name = serializers.CharField(source="team.name", read_only=True)
    lists = SubscriberListSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    engagement_score = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Subscriber
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "status",
            "team",
            "team_name",
            "lists",
            "tags",
            "custom_fields",
            "engagement_score",
            "last_activity",
            "odoo_contact_id",
            "gdpr_consent",
            "gdpr_consent_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        # Extract many-to-many fields
        lists = validated_data.pop("lists", [])
        tags = validated_data.pop("tags", [])

        # Create subscriber
        subscriber = Subscriber.objects.create(**validated_data)

        # Set many-to-many relationships
        subscriber.lists.set(lists)
        subscriber.tags.set(tags)

        return subscriber

    def update(self, instance, validated_data):
        # Extract many-to-many fields
        lists = validated_data.pop("lists", None)
        tags = validated_data.pop("tags", None)

        # Update subscriber
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update many-to-many relationships if provided
        if lists is not None:
            instance.lists.set(lists)
        if tags is not None:
            instance.tags.set(tags)

        return instance


class SubscriberCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating subscribers with validation"""

    lists = serializers.PrimaryKeyRelatedField(
        queryset=SubscriberList.objects.all(), many=True, required=False
    )

    class Meta:
        model = Subscriber
        fields = [
            "email",
            "first_name",
            "last_name",
            "status",
            "lists",
            "tags",
            "custom_fields",
            "gdpr_consent",
        ]

    def validate_email(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Email cannot be empty")
        return value.strip().lower()

    def validate_first_name(self, value):
        if value:
            return value.strip()
        return value

    def validate_last_name(self, value):
        if value:
            return value.strip()
        return value


class SubscriberListCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating subscriber lists with validation"""

    class Meta:
        model = SubscriberList
        fields = [
            "name",
            "description",
            "is_active",
        ]

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()


class SegmentRuleSerializer(serializers.ModelSerializer):
    """Serializer for SegmentRule model"""

    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = SegmentRule
        fields = [
            "id",
            "name",
            "description",
            "team",
            "team_name",
            "field",
            "operator",
            "value",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SubscriberImportSerializer(serializers.Serializer):
    """Serializer for subscriber import validation"""

    file = serializers.FileField()
    list_id = serializers.IntegerField()
    update_existing = serializers.BooleanField(default=False)
    skip_duplicates = serializers.BooleanField(default=True)


class SubscriberExportSerializer(serializers.Serializer):
    """Serializer for subscriber export configuration"""

    list_id = serializers.IntegerField()
    format = serializers.ChoiceField(choices=["csv", "xlsx"], default="csv")
    fields = serializers.ListField(child=serializers.CharField(), required=False)
    include_custom_fields = serializers.BooleanField(default=True)


class SubscriberStatsSerializer(serializers.Serializer):
    """Serializer for subscriber statistics"""

    total_subscribers = serializers.IntegerField()
    active_subscribers = serializers.IntegerField()
    unsubscribed_subscribers = serializers.IntegerField()
    bounced_subscribers = serializers.IntegerField()
    new_this_month = serializers.IntegerField()
    engagement_score_avg = serializers.FloatField()
    top_tags = serializers.ListField(child=serializers.DictField())
    growth_rate = serializers.FloatField()


class SubscriberBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk subscriber actions"""

    action = serializers.ChoiceField(
        choices=[
            "subscribe",
            "unsubscribe",
            "delete",
            "add_tag",
            "remove_tag",
            "add_to_list",
            "remove_from_list",
        ]
    )
    subscriber_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    tag_id = serializers.IntegerField(required=False)
    list_id = serializers.IntegerField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
