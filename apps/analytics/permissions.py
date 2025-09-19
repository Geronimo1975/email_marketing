from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist


class CanViewAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can view analytics.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can view analytics
        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all analytics
        if request.user.is_admin:
            return True

        # Campaign managers can view analytics for their teams
        try:
            if hasattr(obj, "campaign"):
                return (
                    request.user.is_campaign_manager
                    and obj.campaign.team.members.filter(id=request.user.id).exists()
                )
            elif hasattr(obj, "subscriber"):
                return (
                    request.user.is_campaign_manager
                    and obj.subscriber.team.members.filter(id=request.user.id).exists()
                )
            else:
                return request.user.is_campaign_manager
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewCampaignAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can view campaign analytics.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all campaign analytics
        if request.user.is_admin:
            return True

        # Campaign managers can view analytics for campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewSubscriberAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can view subscriber analytics.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all subscriber analytics
        if request.user.is_admin:
            return True

        # Campaign managers can view analytics for subscribers in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanExportAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can export analytics data.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can export analytics
        return request.user.is_campaign_manager


class CanViewEmailEvents(permissions.BasePermission):
    """
    Custom permission to check if user can view email events.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all email events
        if request.user.is_admin:
            return True

        # Campaign managers can view events for campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.campaign.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewReports(permissions.BasePermission):
    """
    Custom permission to check if user can view reports.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all reports
        if request.user.is_admin:
            return True

        # Campaign managers can view reports for campaigns in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.campaign.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanManageAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can manage analytics data.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Only admins can manage analytics data
        return request.user.is_admin

    def has_object_permission(self, request, view, obj):
        # Only admins can manage analytics data
        return request.user.is_admin


class CanViewRealTimeAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can view real-time analytics.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can view real-time analytics
        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all real-time analytics
        if request.user.is_admin:
            return True

        # Campaign managers can view real-time analytics for their teams
        try:
            if hasattr(obj, "campaign"):
                return (
                    request.user.is_campaign_manager
                    and obj.campaign.team.members.filter(id=request.user.id).exists()
                )
            else:
                return request.user.is_campaign_manager
        except (AttributeError, ObjectDoesNotExist):
            return False
