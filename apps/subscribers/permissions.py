from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist


class IsTeamMember(permissions.BasePermission):
    """
    Custom permission to only allow team members to access subscribers.
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

        # Check if user is a member of the subscriber's team
        try:
            return obj.team.members.filter(id=request.user.id).exists()
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanManageSubscribers(permissions.BasePermission):
    """
    Custom permission to only allow users to manage subscribers.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can manage subscribers
        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can do everything
        if request.user.is_admin:
            return True

        # Campaign managers can manage subscribers in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewSubscriber(permissions.BasePermission):
    """
    Custom permission to check if user can view a specific subscriber.
    """

    def has_object_permission(self, request, view, obj):
        # Admin can view everything
        if request.user.is_admin:
            return True

        # Team members can view subscribers in their teams
        try:
            return obj.team.members.filter(id=request.user.id).exists()
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanImportSubscribers(permissions.BasePermission):
    """
    Custom permission to check if user can import subscribers.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can import to any list
        if request.user.is_admin:
            return True

        # Campaign managers can import to lists in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanExportSubscribers(permissions.BasePermission):
    """
    Custom permission to check if user can export subscribers.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can export from any list
        if request.user.is_admin:
            return True

        # Campaign managers can export from lists in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanBulkUpdateSubscribers(permissions.BasePermission):
    """
    Custom permission to check if user can perform bulk updates on subscribers.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager


class CanManageSubscriberLists(permissions.BasePermission):
    """
    Custom permission to check if user can manage subscriber lists.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can manage any list
        if request.user.is_admin:
            return True

        # Campaign managers can manage lists in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanManageTags(permissions.BasePermission):
    """
    Custom permission to check if user can manage tags.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can manage any tag
        if request.user.is_admin:
            return True

        # Campaign managers can manage tags in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanManageSegmentRules(permissions.BasePermission):
    """
    Custom permission to check if user can manage segment rules.
    """

    def has_permission(self, request, view):
        # Must be authenticated and be a campaign manager
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can manage any rule
        if request.user.is_admin:
            return True

        # Campaign managers can manage rules in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False
