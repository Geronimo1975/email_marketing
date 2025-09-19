from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with additional fields for email marketing platform."""

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        CAMPAIGN_MANAGER = 'campaign_manager', _('Campaign Manager')
        VIEWER = 'viewer', _('Viewer')

    email = models.EmailField(_('Email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text=_('User role determines access permissions')
    )
    company_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        db_table = 'users'

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_campaign_manager(self):
        return self.role in [self.Role.ADMIN, self.Role.CAMPAIGN_MANAGER]


class Team(models.Model):
    """Team model for organizing users and campaigns."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_teams'
    )
    members = models.ManyToManyField(
        User,
        through='TeamMembership',
        related_name='teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Team')
        verbose_name_plural = _('Teams')
        db_table = 'teams'

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """Through model for Team-User relationship with additional fields."""

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Team Admin')
        MEMBER = 'member', _('Team Member')

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['team', 'user']
        verbose_name = _('Team Membership')
        verbose_name_plural = _('Team Memberships')
        db_table = 'team_memberships'

    def __str__(self):
        return f'{self.user.email} - {self.team.name} ({self.role})'


class APIKey(models.Model):
    """API keys for external integrations."""

    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('API Key')
        verbose_name_plural = _('API Keys')
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.user.email}'