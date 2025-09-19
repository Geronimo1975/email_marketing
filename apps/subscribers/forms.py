from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Subscriber, SubscriberList, Tag, SegmentRule
from apps.accounts.models import Team


class SubscriberForm(forms.ModelForm):
    """Form for creating and editing subscribers"""

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
        widgets = {
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "subscriber@example.com"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "First Name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Last Name"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "lists": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "tags": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
            "custom_fields": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": '{"company": "Example Corp", "position": "Manager"}',
                }
            ),
            "gdpr_consent": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter lists and tags by user's teams
        if user:
            if user.is_admin:
                self.fields["lists"].queryset = SubscriberList.objects.all()
                self.fields["tags"].queryset = Tag.objects.all()
            else:
                user_teams = user.teams.all()
                self.fields["lists"].queryset = SubscriberList.objects.filter(
                    team__in=user_teams
                )
                self.fields["tags"].queryset = Tag.objects.filter(team__in=user_teams)

        # Set default values
        if not self.instance.pk:  # New subscriber
            self.fields["status"].initial = Subscriber.Status.SUBSCRIBED
            self.fields["gdpr_consent"].initial = True

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email or len(email.strip()) == 0:
            raise ValidationError("Email cannot be empty")
        return email.strip().lower()

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if first_name:
            return first_name.strip()
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if last_name:
            return last_name.strip()
        return last_name

    def clean_custom_fields(self):
        custom_fields = self.cleaned_data.get("custom_fields")
        if custom_fields:
            try:
                import json

                json.loads(custom_fields)
            except json.JSONDecodeError:
                raise ValidationError("Custom fields must be valid JSON")
        return custom_fields


class SubscriberListForm(forms.ModelForm):
    """Form for creating and editing subscriber lists"""

    class Meta:
        model = SubscriberList
        fields = [
            "name",
            "description",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "List Name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "List description",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set default values
        if not self.instance.pk:  # New list
            self.fields["is_active"].initial = True

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or len(name.strip()) == 0:
            raise ValidationError("Name cannot be empty")
        return name.strip()


class TagForm(forms.ModelForm):
    """Form for creating and editing tags"""

    class Meta:
        model = Tag
        fields = [
            "name",
            "color",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tag Name"}
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                    "value": "#3b82f6",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or len(name.strip()) == 0:
            raise ValidationError("Name cannot be empty")
        return name.strip()


class SegmentRuleForm(forms.ModelForm):
    """Form for creating and editing segment rules"""

    class Meta:
        model = SegmentRule
        fields = [
            "name",
            "description",
            "field_name",
            "operator",
            "value",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Rule Name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Rule description",
                }
            ),
            "field_name": forms.Select(attrs={"class": "form-control"}),
            "operator": forms.Select(attrs={"class": "form-control"}),
            "value": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Value"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set field choices
        self.fields["field"].choices = [
            ("email", "Email"),
            ("first_name", "First Name"),
            ("last_name", "Last Name"),
            ("status", "Status"),
            ("created_at", "Created Date"),
            ("last_activity", "Last Activity"),
        ]

        self.fields["operator"].choices = [
            ("equals", "Equals"),
            ("contains", "Contains"),
            ("starts_with", "Starts With"),
            ("ends_with", "Ends With"),
            ("is_empty", "Is Empty"),
            ("is_not_empty", "Is Not Empty"),
            ("greater_than", "Greater Than"),
            ("less_than", "Less Than"),
            ("date_after", "Date After"),
            ("date_before", "Date Before"),
        ]

        # Set default values
        if not self.instance.pk:  # New rule
            self.fields["is_active"].initial = True

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or len(name.strip()) == 0:
            raise ValidationError("Name cannot be empty")
        return name.strip()


class SubscriberImportForm(forms.Form):
    """Form for importing subscribers"""

    file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": ".csv,.xlsx,.xls",
            }
        )
    )
    list_id = forms.ModelChoiceField(
        queryset=SubscriberList.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    update_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.is_admin:
                self.fields["list_id"].queryset = SubscriberList.objects.all()
            else:
                user_teams = user.teams.all()
                self.fields["list_id"].queryset = SubscriberList.objects.filter(
                    team__in=user_teams
                )

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB")

            # Check file extension
            allowed_extensions = [".csv", ".xlsx", ".xls"]
            file_extension = file.name.lower().split(".")[-1]
            if f".{file_extension}" not in allowed_extensions:
                raise ValidationError(
                    "File must be CSV or Excel format (.csv, .xlsx, .xls)"
                )

        return file


class SubscriberFilterForm(forms.Form):
    """Form for filtering subscribers"""

    STATUS_CHOICES = [("", "All Statuses")] + list(Subscriber.Status.choices)

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search subscribers..."}
        ),
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    list_id = forms.ModelChoiceField(
        queryset=SubscriberList.objects.none(),
        required=False,
        empty_label="All Lists",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    tag_id = forms.ModelChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        empty_label="All Tags",
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.is_admin:
                self.fields["list_id"].queryset = SubscriberList.objects.all()
                self.fields["tag_id"].queryset = Tag.objects.all()
            else:
                user_teams = user.teams.all()
                self.fields["list_id"].queryset = SubscriberList.objects.filter(
                    team__in=user_teams
                )
                self.fields["tag_id"].queryset = Tag.objects.filter(team__in=user_teams)


class SubscriberBulkActionForm(forms.Form):
    """Form for bulk subscriber actions"""

    ACTION_CHOICES = [
        ("subscribe", "Subscribe"),
        ("unsubscribe", "Unsubscribe"),
        ("delete", "Delete"),
        ("add_tag", "Add Tag"),
        ("remove_tag", "Remove Tag"),
        ("add_to_list", "Add to List"),
        ("remove_from_list", "Remove from List"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    subscriber_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
    )
    tag_id = forms.ModelChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        empty_label="Select Tag",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    list_id = forms.ModelChoiceField(
        queryset=SubscriberList.objects.none(),
        required=False,
        empty_label="Select List",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Reason for action (optional)",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            if user.is_admin:
                self.fields["tag_id"].queryset = Tag.objects.all()
                self.fields["list_id"].queryset = SubscriberList.objects.all()
            else:
                user_teams = user.teams.all()
                self.fields["tag_id"].queryset = Tag.objects.filter(team__in=user_teams)
                self.fields["list_id"].queryset = SubscriberList.objects.filter(
                    team__in=user_teams
                )

    def clean_subscriber_ids(self):
        subscriber_ids = self.cleaned_data.get("subscriber_ids")
        if subscriber_ids:
            try:
                import json

                ids = json.loads(subscriber_ids)
                if not isinstance(ids, list) or not ids:
                    raise ValidationError("No subscribers selected")
                return ids
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Invalid subscriber selection")
        raise ValidationError("No subscribers selected")
