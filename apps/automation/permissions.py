from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist


class CanManageAutomation(permissions.BasePermission):
    """
    Custom permission to check if user can manage automation workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin and campaign managers can manage automation
        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can manage all automation
        if request.user.is_admin:
            return True

        # Campaign managers can manage automation for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanExecuteWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can execute workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can execute all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can execute workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can view workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can view workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanEditWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can edit workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can edit all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can edit workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanCreateWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can create workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager


class CanDeleteWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can delete workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can delete all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can delete workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanManageWorkflowSteps(permissions.BasePermission):
    """
    Custom permission to check if user can manage workflow steps.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can manage all workflow steps
        if request.user.is_admin:
            return True

        # Campaign managers can manage steps for workflows in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.workflow.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewWorkflowAnalytics(permissions.BasePermission):
    """
    Custom permission to check if user can view workflow analytics.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all workflow analytics
        if request.user.is_admin:
            return True

        # Campaign managers can view analytics for workflows in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanExportWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can export workflow data.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can export all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can export workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanImportWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can import workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager


class CanPauseWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can pause workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can pause all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can pause workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanResumeWorkflow(permissions.BasePermission):
    """
    Custom permission to check if user can resume workflows.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can resume all workflows
        if request.user.is_admin:
            return True

        # Campaign managers can resume workflows for their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False


class CanViewWorkflowSubscribers(permissions.BasePermission):
    """
    Custom permission to check if user can view workflow subscribers.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_campaign_manager

    def has_object_permission(self, request, view, obj):
        # Admin can view all workflow subscribers
        if request.user.is_admin:
            return True

        # Campaign managers can view subscribers for workflows in their teams
        try:
            return (
                request.user.is_campaign_manager
                and obj.workflow.team.members.filter(id=request.user.id).exists()
            )
        except (AttributeError, ObjectDoesNotExist):
            return False
