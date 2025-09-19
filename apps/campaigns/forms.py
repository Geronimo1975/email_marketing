from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Campaign, EmailTemplate
from apps.subscribers.models import SubscriberList, Tag


class CampaignForm(forms.ModelForm):
    """Form for creating and editing campaigns"""

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
            "ab_test_percentage",
            "ab_winner_criteria",
            "ab_test_duration",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter campaign name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe your campaign",
                }
            ),
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Email subject line"}
            ),
            "from_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "sender@example.com"}
            ),
            "from_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Sender Name"}
            ),
            "reply_to": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "reply@example.com"}
            ),
            "html_content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 15,
                    "placeholder": "Enter your HTML email content",
                }
            ),
            "text_content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": "Enter plain text version (optional)",
                }
            ),
            "send_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "timezone": forms.Select(attrs={"class": "form-control"}),
            "ab_test_percentage": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 100}
            ),
            "ab_test_duration": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 168}  # 1 week max
            ),
            "ab_winner_criteria": forms.Select(attrs={"class": "form-control"}),
            "subscriber_lists": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
            "tags": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "track_opens": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "track_clicks": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter subscriber lists and tags by user's teams
        if user:
            if user.is_admin:
                self.fields["subscriber_lists"].queryset = SubscriberList.objects.all()
                self.fields["tags"].queryset = Tag.objects.all()
            else:
                user_teams = user.teams.all()
                self.fields["subscriber_lists"].queryset = (
                    SubscriberList.objects.filter(team__in=user_teams)
                )
                self.fields["tags"].queryset = Tag.objects.filter(team__in=user_teams)

        # Set default values
        if not self.instance.pk:  # New campaign
            self.fields["from_email"].initial = user.email if user else ""
            self.fields["from_name"].initial = user.get_full_name() if user else ""
            self.fields["timezone"].initial = user.timezone if user else "UTC"
            self.fields["track_opens"].initial = True
            self.fields["track_clicks"].initial = True

    def clean_subject(self):
        subject = self.cleaned_data.get("subject")
        if not subject or len(subject.strip()) == 0:
            raise ValidationError("Subject cannot be empty")
        return subject.strip()

    def clean_html_content(self):
        html_content = self.cleaned_data.get("html_content")
        if not html_content or len(html_content.strip()) == 0:
            raise ValidationError("HTML content cannot be empty")
        return html_content.strip()

    def clean_subscriber_lists(self):
        subscriber_lists = self.cleaned_data.get("subscriber_lists")
        if not subscriber_lists:
            raise ValidationError("At least one subscriber list is required")
        return subscriber_lists

    def clean_send_at(self):
        send_at = self.cleaned_data.get("send_at")
        if send_at and send_at <= timezone.now():
            raise ValidationError("Send time must be in the future")
        return send_at

    def clean_ab_test_percentage(self):
        percentage = self.cleaned_data.get("ab_test_percentage")
        if percentage and (percentage < 1 or percentage > 100):
            raise ValidationError("A/B test percentage must be between 1 and 100")
        return percentage


class EmailTemplateForm(forms.ModelForm):
    """Form for creating and editing email templates"""

    class Meta:
        model = EmailTemplate
        fields = [
            "name",
            "description",
            "type",
            "subject",
            "html_content",
            "text_content",
            "variables",
            "thumbnail",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Template name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Template description",
                }
            ),
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Email subject line"}
            ),
            "html_content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 15,
                    "placeholder": "Enter HTML template content",
                }
            ),
            "text_content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": "Enter plain text version (optional)",
                }
            ),
            "variables": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter available variables (one per line)",
                }
            ),
            "thumbnail": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set default values
        if not self.instance.pk:  # New template
            self.fields["is_active"].initial = True

    def clean_subject(self):
        subject = self.cleaned_data.get("subject")
        if not subject or len(subject.strip()) == 0:
            raise ValidationError("Subject cannot be empty")
        return subject.strip()

    def clean_html_content(self):
        html_content = self.cleaned_data.get("html_content")
        if not html_content or len(html_content.strip()) == 0:
            raise ValidationError("HTML content cannot be empty")
        return html_content.strip()

    def clean_variables(self):
        variables = self.cleaned_data.get("variables")
        if variables:
            # Convert to list if it's a string
            if isinstance(variables, str):
                variables = [v.strip() for v in variables.split("\n") if v.strip()]
            return variables
        return []


class CampaignFilterForm(forms.Form):
    """Form for filtering campaigns"""

    STATUS_CHOICES = [("", "All Statuses")] + list(Campaign.Status.choices)
    TYPE_CHOICES = [("", "All Types")] + list(Campaign.Type.choices)

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search campaigns..."}
        ),
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class CampaignScheduleForm(forms.Form):
    """Form for scheduling campaigns"""

    send_at = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        )
    )
    timezone = forms.ChoiceField(
        choices=[
            ("UTC", "UTC"),
            ("Europe/Bucharest", "Europe/Bucharest"),
            ("America/New_York", "America/New_York"),
            ("America/Los_Angeles", "America/Los_Angeles"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_send_at(self):
        send_at = self.cleaned_data.get("send_at")
        if send_at and send_at <= timezone.now():
            raise ValidationError("Send time must be in the future")
        return send_at
