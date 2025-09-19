from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.utils import timezone


class AutomationWorkflow(models.Model):
    """Automated email workflows and drip campaigns."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        ACTIVE = 'active', _('Active')
        PAUSED = 'paused', _('Paused')
        ARCHIVED = 'archived', _('Archived')

    class TriggerType(models.TextChoices):
        SUBSCRIBER_ADDED = 'subscriber_added', _('Subscriber Added to List')
        TAG_ADDED = 'tag_added', _('Tag Added to Subscriber')
        EMAIL_OPENED = 'email_opened', _('Email Opened')
        EMAIL_CLICKED = 'email_clicked', _('Email Link Clicked')
        DATE_BASED = 'date_based', _('Date-based (Anniversary, etc.)')
        CUSTOM_EVENT = 'custom_event', _('Custom Event')
        API_TRIGGER = 'api_trigger', _('API Trigger')

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    team = models.ForeignKey(
        'accounts.Team',
        on_delete=models.CASCADE,
        related_name='automation_workflows'
    )

    # Trigger configuration
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices)
    trigger_config = JSONField(default=dict)  # Trigger-specific settings

    # Entry conditions
    entry_conditions = JSONField(default=list)  # List of conditions that must be met
    exit_conditions = JSONField(default=list)  # Conditions that remove from workflow

    # Settings
    allow_re_entry = models.BooleanField(default=False)
    max_entries_per_subscriber = models.IntegerField(default=1)

    # Statistics
    total_entries = models.IntegerField(default=0)
    active_subscribers = models.IntegerField(default=0)
    completed_workflows = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_workflows'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Automation Workflow')
        verbose_name_plural = _('Automation Workflows')
        db_table = 'automation_workflows'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def completion_rate(self):
        if self.total_entries > 0:
            return (self.completed_workflows / self.total_entries) * 100
        return 0


class WorkflowStep(models.Model):
    """Individual steps in an automation workflow."""

    class StepType(models.TextChoices):
        EMAIL = 'email', _('Send Email')
        DELAY = 'delay', _('Wait/Delay')
        CONDITION = 'condition', _('Conditional Branch')
        TAG_ACTION = 'tag_action', _('Add/Remove Tag')
        LIST_ACTION = 'list_action', _('Add/Remove from List')
        WEBHOOK = 'webhook', _('Send Webhook')
        UPDATE_FIELD = 'update_field', _('Update Custom Field')
        GOAL = 'goal', _('Goal/Conversion')

    workflow = models.ForeignKey(
        AutomationWorkflow,
        on_delete=models.CASCADE,
        related_name='steps'
    )

    name = models.CharField(max_length=255)
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    order = models.IntegerField()  # Order within the workflow

    # Step configuration
    config = JSONField(default=dict)  # Step-specific settings

    # Email step specific
    email_template = models.ForeignKey(
        'campaigns.EmailTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_steps'
    )

    # Delay step specific
    delay_amount = models.IntegerField(null=True, blank=True)  # Amount to delay
    delay_unit = models.CharField(
        max_length=20,
        choices=[
            ('minutes', _('Minutes')),
            ('hours', _('Hours')),
            ('days', _('Days')),
            ('weeks', _('Weeks')),
        ],
        blank=True
    )

    # Conditional step
    conditions = JSONField(default=list, blank=True)  # List of conditions
    true_path_step = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='true_path_from'
    )
    false_path_step = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='false_path_from'
    )

    # Next step (for linear workflows)
    next_step = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_steps'
    )

    # Statistics
    subscribers_entered = models.IntegerField(default=0)
    subscribers_completed = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['workflow', 'order']
        verbose_name = _('Workflow Step')
        verbose_name_plural = _('Workflow Steps')
        db_table = 'workflow_steps'
        ordering = ['workflow', 'order']

    def __str__(self):
        return f'{self.workflow.name} - Step {self.order}: {self.name}'

    @property
    def completion_rate(self):
        if self.subscribers_entered > 0:
            return (self.subscribers_completed / self.subscribers_entered) * 100
        return 0


class WorkflowSubscriber(models.Model):
    """Tracks subscribers currently in automation workflows."""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        EXITED = 'exited', _('Exited')
        PAUSED = 'paused', _('Paused')
        FAILED = 'failed', _('Failed')

    workflow = models.ForeignKey(
        AutomationWorkflow,
        on_delete=models.CASCADE,
        related_name='workflow_subscribers'
    )
    subscriber = models.ForeignKey(
        'subscribers.Subscriber',
        on_delete=models.CASCADE,
        related_name='workflow_subscriptions'
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    current_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_subscribers'
    )

    # Timing
    entered_at = models.DateTimeField(auto_now_add=True)
    next_action_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    exited_at = models.DateTimeField(null=True, blank=True)

    # Progress tracking
    steps_completed = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)

    # Context data
    entry_data = JSONField(default=dict, blank=True)  # Data at time of entry
    current_data = JSONField(default=dict, blank=True)  # Current context data

    # Exit reason
    exit_reason = models.CharField(max_length=255, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['workflow', 'subscriber']
        verbose_name = _('Workflow Subscriber')
        verbose_name_plural = _('Workflow Subscribers')
        db_table = 'workflow_subscribers'
        ordering = ['-entered_at']
        indexes = [
            models.Index(fields=['status', 'next_action_at']),
            models.Index(fields=['workflow', 'status']),
        ]

    def __str__(self):
        return f'{self.subscriber.email} in {self.workflow.name}'

    @property
    def time_in_workflow(self):
        """Calculate time spent in workflow."""
        end_time = self.completed_at or self.exited_at or timezone.now()
        return end_time - self.entered_at