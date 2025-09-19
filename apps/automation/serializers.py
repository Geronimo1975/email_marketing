from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    AutomationWorkflow,
    WorkflowStep,
    WorkflowSubscriber,
)

User = get_user_model()


class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStep model"""

    class Meta:
        model = WorkflowStep
        fields = [
            "id",
            "workflow",
            "step_type",
            "name",
            "description",
            "order",
            "config",
            "conditions",
            "delay_hours",
            "delay_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AutomationWorkflowSerializer(serializers.ModelSerializer):
    """Serializer for AutomationWorkflow model"""

    steps = WorkflowStepSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    team_name = serializers.CharField(source="team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    trigger_type_display = serializers.CharField(
        source="get_trigger_type_display", read_only=True
    )

    class Meta:
        model = AutomationWorkflow
        fields = [
            "id",
            "name",
            "description",
            "trigger_type",
            "trigger_type_display",
            "trigger_config",
            "conditions",
            "status",
            "status_display",
            "is_active",
            "team",
            "team_name",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "last_executed",
            "execution_count",
            "steps",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "last_executed",
            "execution_count",
        ]


class WorkflowSubscriberSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowSubscriber model"""

    subscriber_email = serializers.CharField(source="subscriber.email", read_only=True)
    subscriber_name = serializers.CharField(
        source="subscriber.first_name", read_only=True
    )
    current_step_name = serializers.CharField(
        source="current_step.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WorkflowSubscriber
        fields = [
            "id",
            "workflow",
            "subscriber",
            "subscriber_email",
            "subscriber_name",
            "status",
            "status_display",
            "current_step",
            "current_step_name",
            "started_at",
            "completed_at",
            "last_activity",
            "metadata",
        ]
        read_only_fields = ["started_at", "completed_at", "last_activity"]


class WorkflowExecutionSerializer(serializers.Serializer):
    """Serializer for workflow execution data"""

    workflow_id = serializers.IntegerField()
    subscriber_ids = serializers.ListField(child=serializers.IntegerField())
    execution_type = serializers.CharField()
    scheduled_at = serializers.DateTimeField(required=False)
    metadata = serializers.DictField(required=False)


class WorkflowStatsSerializer(serializers.Serializer):
    """Serializer for workflow statistics"""

    # Basic counts
    total_workflows = serializers.IntegerField()
    active_workflows = serializers.IntegerField()
    paused_workflows = serializers.IntegerField()
    completed_workflows = serializers.IntegerField()

    # Subscriber counts
    total_subscribers = serializers.IntegerField()
    active_subscribers = serializers.IntegerField()
    completed_subscribers = serializers.IntegerField()
    failed_subscribers = serializers.IntegerField()

    # Performance metrics
    average_execution_time = serializers.FloatField()
    success_rate = serializers.FloatField()
    completion_rate = serializers.FloatField()

    # Recent activity
    recent_executions = serializers.ListField(child=serializers.DictField())
    top_performing_workflows = serializers.ListField(child=serializers.DictField())


class WorkflowPerformanceSerializer(serializers.Serializer):
    """Serializer for workflow performance data"""

    # Execution metrics
    total_executions = serializers.IntegerField()
    successful_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    success_rate = serializers.FloatField()

    # Subscriber metrics
    total_subscribers = serializers.IntegerField()
    active_subscribers = serializers.IntegerField()
    completed_subscribers = serializers.IntegerField()
    completion_rate = serializers.FloatField()

    # Timing metrics
    average_execution_time = serializers.FloatField()
    fastest_execution = serializers.FloatField()
    slowest_execution = serializers.FloatField()

    # Step performance
    step_performance = serializers.ListField(child=serializers.DictField())

    # Recent activity
    recent_activity = serializers.ListField(child=serializers.DictField())


class WorkflowTriggerSerializer(serializers.Serializer):
    """Serializer for workflow trigger configuration"""

    trigger_type = serializers.CharField()
    trigger_config = serializers.DictField()
    conditions = serializers.DictField(required=False)
    delay_hours = serializers.IntegerField(default=0)
    delay_days = serializers.IntegerField(default=0)


class WorkflowConditionSerializer(serializers.Serializer):
    """Serializer for workflow conditions"""

    field = serializers.CharField()
    operator = serializers.CharField()
    value = serializers.CharField()
    logical_operator = serializers.CharField(default="AND")


class WorkflowStepConfigSerializer(serializers.Serializer):
    """Serializer for workflow step configuration"""

    step_type = serializers.CharField()
    config = serializers.DictField()
    conditions = serializers.ListField(child=WorkflowConditionSerializer())
    delay_hours = serializers.IntegerField(default=0)
    delay_days = serializers.IntegerField(default=0)


class WorkflowExecutionStatusSerializer(serializers.Serializer):
    """Serializer for workflow execution status"""

    execution_id = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.FloatField()
    subscribers_processed = serializers.IntegerField()
    total_subscribers = serializers.IntegerField()
    current_step = serializers.CharField()
    started_at = serializers.DateTimeField()
    estimated_completion = serializers.DateTimeField(required=False)
    error_message = serializers.CharField(required=False)


class WorkflowSubscriberStatusSerializer(serializers.Serializer):
    """Serializer for subscriber status in workflow"""

    subscriber_id = serializers.IntegerField()
    subscriber_email = serializers.CharField()
    status = serializers.CharField()
    current_step = serializers.CharField()
    progress_percentage = serializers.FloatField()
    started_at = serializers.DateTimeField()
    last_activity = serializers.DateTimeField()
    estimated_completion = serializers.DateTimeField(required=False)


class WorkflowTemplateSerializer(serializers.Serializer):
    """Serializer for workflow templates"""

    name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    trigger_type = serializers.CharField()
    steps = serializers.ListField(child=WorkflowStepConfigSerializer())
    estimated_duration = serializers.IntegerField()  # in hours
    complexity = serializers.CharField()  # simple, medium, complex
    tags = serializers.ListField(child=serializers.CharField())


class WorkflowAnalyticsSerializer(serializers.Serializer):
    """Serializer for workflow analytics"""

    # Time-based metrics
    executions_today = serializers.IntegerField()
    executions_this_week = serializers.IntegerField()
    executions_this_month = serializers.IntegerField()

    # Performance trends
    daily_executions = serializers.ListField(child=serializers.DictField())
    weekly_performance = serializers.ListField(child=serializers.DictField())
    monthly_performance = serializers.ListField(child=serializers.DictField())

    # Subscriber engagement
    subscriber_engagement = serializers.DictField()
    step_completion_rates = serializers.ListField(child=serializers.DictField())

    # Error analysis
    error_breakdown = serializers.ListField(child=serializers.DictField())
    common_failure_points = serializers.ListField(child=serializers.DictField())


class WorkflowExportSerializer(serializers.Serializer):
    """Serializer for workflow export data"""

    workflow = AutomationWorkflowSerializer()
    steps = WorkflowStepSerializer(many=True)
    subscribers = WorkflowSubscriberSerializer(many=True)
    performance = WorkflowPerformanceSerializer()
    analytics = WorkflowAnalyticsSerializer()
    export_date = serializers.DateTimeField()
    export_version = serializers.CharField()
