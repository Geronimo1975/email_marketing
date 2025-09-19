from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import (
    EmailEvent,
    CampaignReport,
    SubscriberActivity,
    LinkClick,
    DomainReputation,
)
from .serializers import (
    EmailEventSerializer,
    CampaignReportSerializer,
    SubscriberActivitySerializer,
    LinkClickSerializer,
    DomainReputationSerializer,
    AnalyticsDashboardSerializer,
)
from .utils import (
    get_dashboard_stats,
    get_campaign_performance,
    get_subscriber_engagement,
    get_email_metrics,
    get_click_analytics,
    get_delivery_analytics,
    get_engagement_timeline,
    get_top_performing_campaigns,
    get_device_breakdown,
    get_location_breakdown,
    get_unsubscribe_analytics,
    get_bounce_analytics,
)
from .permissions import IsTeamMember, CanViewAnalytics

import json
import logging
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


# Template Views
class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Main analytics dashboard"""

    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get date range from request
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        else:
            date_from = timezone.now().date() - timedelta(days=30)

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        else:
            date_to = timezone.now().date()

        # Get dashboard data
        context.update(
            {
                "stats": get_dashboard_stats(user, date_from, date_to),
                "campaign_performance": get_campaign_performance(
                    user, date_from, date_to
                ),
                "subscriber_engagement": get_subscriber_engagement(
                    user, date_from, date_to
                ),
                "email_metrics": get_email_metrics(user, date_from, date_to),
                "engagement_timeline": get_engagement_timeline(
                    user, date_from, date_to
                ),
                "top_campaigns": get_top_performing_campaigns(user, date_from, date_to),
                "device_breakdown": get_device_breakdown(user, date_from, date_to),
                "location_breakdown": get_location_breakdown(user, date_from, date_to),
                "date_from": date_from,
                "date_to": date_to,
            }
        )

        return context


class AnalyticsAPIView(APIView):
    def get(self, request):
        return Response({"message": "Analytics API"}, status=status.HTTP_200_OK)
