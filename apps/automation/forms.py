from django import forms
from django.contrib.auth import get_user_model
from .models import (
    AutomationWorkflow,
    WorkflowStep,
    WorkflowSubscriber,
)

User = get_user_model()


class AutomationWorkflowForm(forms.ModelForm):
    """Form for creating and editing automation workflows"""

    class Meta:
        model = AutomationWorkflow
        fields = [
            "name",
            "description",
            "trigger_type",
            "trigger_config",
            "conditions",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter workflow name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe what this workflow does",
                }
            ),
            "trigger_type": forms.Select(attrs={"class": "form-select"}),
            "trigger_config": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter trigger configuration as JSON",
                }
            ),
            "conditions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter conditions as JSON",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_trigger_config(self):
        """Validate trigger configuration JSON"""
        config = self.cleaned_data.get("trigger_config")
        if config:
            try:
                import json

                json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError(
                    "Invalid JSON format for trigger configuration"
                )
        return config

    def clean_conditions(self):
        """Validate conditions JSON"""
        conditions = self.cleaned_data.get("conditions")
        if conditions:
            try:
                import json

                json.loads(conditions)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for conditions")
        return conditions


class WorkflowStepForm(forms.ModelForm):
    """Form for creating and editing workflow steps"""

    class Meta:
        model = WorkflowStep
        fields = [
            "step_type",
            "name",
            "description",
            "order",
            "config",
            "conditions",
            "delay_hours",
            "delay_days",
            "is_active",
        ]
        widgets = {
            "step_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter step name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Describe what this step does",
                }
            ),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "config": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter step configuration as JSON",
                }
            ),
            "conditions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter step conditions as JSON",
                }
            ),
            "delay_hours": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "max": 23}
            ),
            "delay_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_config(self):
        """Validate step configuration JSON"""
        config = self.cleaned_data.get("config")
        if config:
            try:
                import json

                json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError(
                    "Invalid JSON format for step configuration"
                )
        return config

    def clean_conditions(self):
        """Validate step conditions JSON"""
        conditions = self.cleaned_data.get("conditions")
        if conditions:
            try:
                import json

                json.loads(conditions)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for step conditions")
        return conditions

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        delay_hours = cleaned_data.get("delay_hours", 0)
        delay_days = cleaned_data.get("delay_days", 0)

        if delay_hours < 0 or delay_hours > 23:
            raise forms.ValidationError("Delay hours must be between 0 and 23")

        if delay_days < 0:
            raise forms.ValidationError("Delay days must be 0 or greater")

        return cleaned_data


class WorkflowTriggerForm(forms.Form):
    """Form for configuring workflow triggers"""

    TRIGGER_CHOICES = [
        ("immediate", "Immediate"),
        ("scheduled", "Scheduled"),
        ("event_based", "Event Based"),
        ("subscriber_action", "Subscriber Action"),
        ("campaign_completion", "Campaign Completion"),
        ("date_based", "Date Based"),
    ]

    trigger_type = forms.ChoiceField(
        choices=TRIGGER_CHOICES, widget=forms.Select(attrs={"class": "form-select"})
    )
    trigger_config = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter trigger configuration as JSON",
            }
        ),
        required=False,
    )
    scheduled_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
        required=False,
    )
    event_type = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter event type"}
        ),
        required=False,
    )

    def clean_trigger_config(self):
        """Validate trigger configuration JSON"""
        config = self.cleaned_data.get("trigger_config")
        if config:
            try:
                import json

                json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError(
                    "Invalid JSON format for trigger configuration"
                )
        return config


class WorkflowConditionForm(forms.Form):
    """Form for configuring workflow conditions"""

    OPERATOR_CHOICES = [
        ("equals", "Equals"),
        ("not_equals", "Not Equals"),
        ("contains", "Contains"),
        ("not_contains", "Not Contains"),
        ("greater_than", "Greater Than"),
        ("less_than", "Less Than"),
        ("is_empty", "Is Empty"),
        ("is_not_empty", "Is Not Empty"),
    ]

    LOGICAL_OPERATOR_CHOICES = [
        ("AND", "AND"),
        ("OR", "OR"),
    ]

    field = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Field name"}
        )
    )
    operator = forms.ChoiceField(
        choices=OPERATOR_CHOICES, widget=forms.Select(attrs={"class": "form-select"})
    )
    value = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Value to compare"}
        ),
        required=False,
    )
    logical_operator = forms.ChoiceField(
        choices=LOGICAL_OPERATOR_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        initial="AND",
    )


class WorkflowExecutionForm(forms.Form):
    """Form for executing workflows"""

    subscriber_ids = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter subscriber IDs (one per line) or email addresses",
            }
        ),
        help_text="Enter subscriber IDs or email addresses, one per line",
    )
    execution_type = forms.ChoiceField(
        choices=[
            ("immediate", "Execute Immediately"),
            ("scheduled", "Schedule for Later"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    scheduled_at = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
        required=False,
    )

    def clean_subscriber_ids(self):
        """Parse and validate subscriber IDs"""
        data = self.cleaned_data.get("subscriber_ids")
        if not data:
            raise forms.ValidationError(
                "Please enter at least one subscriber ID or email"
            )

        # Split by lines and clean
        subscriber_inputs = [line.strip() for line in data.split("\n") if line.strip()]

        if not subscriber_inputs:
            raise forms.ValidationError(
                "Please enter at least one subscriber ID or email"
            )

        return subscriber_inputs


class WorkflowFilterForm(forms.Form):
    """Form for filtering workflows"""

    STATUS_CHOICES = [
        ("", "All Statuses"),
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
    ]

    TRIGGER_CHOICES = [
        ("", "All Triggers"),
        ("immediate", "Immediate"),
        ("scheduled", "Scheduled"),
        ("event_based", "Event Based"),
        ("subscriber_action", "Subscriber Action"),
        ("campaign_completion", "Campaign Completion"),
        ("date_based", "Date Based"),
    ]

    search = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search workflows..."}
        ),
        required=False,
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    trigger_type = forms.ChoiceField(
        choices=TRIGGER_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    is_active = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}), required=False
    )


class WorkflowStepReorderForm(forms.Form):
    """Form for reordering workflow steps"""

    step_orders = forms.CharField(widget=forms.HiddenInput())

    def clean_step_orders(self):
        """Validate step order data"""
        data = self.cleaned_data.get("step_orders")
        if not data:
            raise forms.ValidationError("No step order data provided")

        try:
            import json

            orders = json.loads(data)
            if not isinstance(orders, list):
                raise forms.ValidationError("Invalid step order format")

            # Validate that all values are integers
            for order in orders:
                if not isinstance(order, int) or order < 1:
                    raise forms.ValidationError("Invalid step order values")

            return orders
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for step orders")


class WorkflowTemplateForm(forms.Form):
    """Form for creating workflows from templates"""

    template_name = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter template name"}
        )
    )
    workflow_name = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter workflow name"}
        )
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter workflow description",
            }
        ),
        required=False,
    )
    customize_settings = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
        initial=False,
    )


class WorkflowAnalyticsForm(forms.Form):
    """Form for workflow analytics filters"""

    date_from = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        required=False,
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        required=False,
    )
    workflow_id = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Workflow ID"}
        ),
        required=False,
    )
    include_subscriber_details = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
        initial=False,
    )

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date")

        return cleaned_data
