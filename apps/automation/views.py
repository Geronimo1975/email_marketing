from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, F
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import AutomationWorkflow, WorkflowStep, WorkflowSubscriber
from .serializers import (
    AutomationWorkflowSerializer,
    WorkflowStepSerializer,
    WorkflowSubscriberSerializer,
    WorkflowExecutionSerializer,
)
from .forms import (
    AutomationWorkflowForm,
    WorkflowStepForm,
    WorkflowTriggerForm,
    WorkflowConditionForm,
)
from .permissions import (
    IsTeamMember,
    CanManageAutomation,
    CanExecuteWorkflow,
    CanViewWorkflow,
    CanEditWorkflow,
)
from .utils import (
    execute_workflow,
    validate_workflow_conditions,
    get_workflow_stats,
    get_subscriber_workflows,
    trigger_workflow_for_subscriber,
    pause_workflow,
    resume_workflow,
    get_workflow_performance,
)
from .tasks import (
    execute_workflow_task,
    process_workflow_triggers,
    cleanup_completed_workflows,
    update_workflow_metrics,
)

import json
import logging
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


# Template Views
class AutomationDashboardView(LoginRequiredMixin, TemplateView):
    """Main automation dashboard"""

    template_name = "automation/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's workflows
        if user.is_admin:
            workflows = AutomationWorkflow.objects.all()
        else:
            workflows = AutomationWorkflow.objects.filter(
                Q(team__members=user) | Q(created_by=user)
            ).distinct()

        # Get workflow statistics
        context.update(
            {
                "workflows": workflows[:10],  # Recent workflows
                "stats": get_workflow_stats(user),
                "active_workflows": workflows.filter(
                    status=AutomationWorkflow.Status.ACTIVE
                ).count(),
                "paused_workflows": workflows.filter(
                    status=AutomationWorkflow.Status.PAUSED
                ).count(),
                "completed_workflows": workflows.filter(
                    status=AutomationWorkflow.Status.COMPLETED
                ).count(),
                "total_subscribers": WorkflowSubscriber.objects.filter(
                    workflow__in=workflows
                ).count(),
            }
        )

        return context


class WorkflowAPIView(APIView):
    def get(self, request):
        return Response(
            {"message": "Automation Workflows API"}, status=status.HTTP_200_OK
        )
