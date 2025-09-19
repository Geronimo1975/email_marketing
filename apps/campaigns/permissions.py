from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist


class IsTeamMember(permissions.BasePermission):
    """
    Custom permission to only allow team members to access campaigns.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can access everything
        if request.user.is_admin:
            return True

        # Check if user is a member of any team
        return request.user.teams.exists()

    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.is_admin:
            return True

        # Check if user is a member of the campaign's team
        try:
            return obj.team.members.filter(id=request.user.id).exists()
        except (AttributeError, ObjectDoesNotExist):
            return False


class IsCampaignManager(permissions.BasePermission):
    """
    Custom permission to only allow campaign managers to perform campaign actions.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can perform actions
        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can do everything
        if request.user.is_admin:
            return True

        # Campaign managers can manage campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class IsCampaignOwner(permissions.BasePermission):
    """
    Custom permission to only allow campaign owners to edit their campaigns.
    """

    def has_object_permission(self, request, view, obj):
        # Admin can do everything
        if request.user.is_admin:
            return True

        # Campaign creator can edit their campaigns
        return obj.created_by == request.user


class CanViewCampaign(permissions.BasePermission):
    """
    Custom permission to check if user can view a specific campaign.
    """

    def has_object_permission(self, request, view, obj):
        # Admin can view everything
        if request.user.is_admin:
            return True

        # Team members can view campaigns in their teams
        try:
            return obj.team.members.filter(id=request.user.id).exists()
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanSendCampaign(permissions.BasePermission):
    """
    Custom permission to check if user can send campaigns.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can send any campaign
        if request.user.is_admin:
            return True

        # Campaign managers can send campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanScheduleCampaign(permissions.BasePermission):
    """
    Custom permission to check if user can schedule campaigns.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can schedule any campaign
        if request.user.is_admin:
            return True

        # Campaign managers can schedule campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanDuplicateCampaign(permissions.BasePermission):
    """
    Custom permission to check if user can duplicate campaigns.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can duplicate any campaign
        if request.user.is_admin:
            return True

        # Campaign managers can duplicate campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False
