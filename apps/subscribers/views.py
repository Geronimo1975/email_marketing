from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Subscriber, SubscriberList, Tag, SegmentRule, Subscription
from .serializers import (
    SubscriberSerializer,
    SubscriberListSerializer,
    TagSerializer,
    SegmentRuleSerializer,
    SubscriptionSerializer,
)
from .tasks import (
    import_subscribers_task,
    export_subscribers_task,
    sync_subscribers_task,
)
from .forms import (
    SubscriberForm,
    SubscriberListForm,
    TagForm,
    SegmentRuleForm,
    SubscriberImportForm,
    SubscriberFilterForm,
)
from .permissions import IsTeamMember, CanManageSubscribers
from .utils import get_subscriber_stats, calculate_engagement_score, segment_subscribers

import json
import logging

logger = logging.getLogger(__name__)


# Template Views
class SubscriberListView(LoginRequiredMixin, ListView):
    model = Subscriber
    template_name = "subscribers/subscriber_list.html"
    context_object_name = "subscribers"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Subscriber.objects.select_related("team").prefetch_related(
                "lists", "tags"
            )
        else:
            return (
                Subscriber.objects.filter(Q(team__members=user) | Q(team__isnull=True))
                .select_related("team")
                .prefetch_related("lists", "tags")
                .distinct()
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = get_subscriber_stats(self.request.user)
        context["recent_subscribers"] = self.get_queryset()[:5]
        context["filter_form"] = SubscriberFilterForm(self.request.GET)
        return context


class SubscriberDetailView(LoginRequiredMixin, DetailView):
    model = Subscriber
    template_name = "subscribers/subscriber_detail.html"
    context_object_name = "subscriber"

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Subscriber.objects.select_related("team").prefetch_related(
                "lists", "tags", "subscriptions"
            )
        else:
            return (
                Subscriber.objects.filter(Q(team__members=user) | Q(team__isnull=True))
                .select_related("team")
                .prefetch_related("lists", "tags", "subscriptions")
                .distinct()
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscriber = self.get_object()

        # Get subscriber metrics
        context["engagement_score"] = calculate_engagement_score(subscriber)
        context["recent_activity"] = self.get_recent_activity(subscriber)
        context["campaign_history"] = self.get_campaign_history(subscriber)

        return context

    def get_recent_activity(self, subscriber):
        """Get recent subscriber activity"""
        from apps.analytics.models import EmailEvent

        return EmailEvent.objects.filter(recipient_email=subscriber.email).order_by(
            "-timestamp"
        )[:10]

    def get_campaign_history(self, subscriber):
        """Get campaign history for subscriber"""
        from apps.campaigns.models import CampaignRecipient

        return (
            CampaignRecipient.objects.filter(subscriber=subscriber)
            .select_related("campaign")
            .order_by("-sent_at")[:10]
        )


class SubscriberCreateView(LoginRequiredMixin, CreateView):
    model = Subscriber
    form_class = SubscriberForm
    template_name = "subscribers/subscriber_form.html"

    def form_valid(self, form):
        form.instance.team = self.request.user.teams.first()

        response = super().form_valid(form)
        messages.success(
            self.request, f'Subscriber "{form.instance.email}" created successfully!'
        )
        return response

    def get_success_url(self):
        return reverse_lazy(
            "subscribers:subscriber_detail", kwargs={"pk": self.object.pk}
        )


class SubscriberAPIView(APIView):
    def get(self, request):
        return Response({"message": "Subscribers API"}, status=status.HTTP_200_OK)
