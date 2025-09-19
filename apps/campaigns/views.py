from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class CampaignListView(TemplateView):
    template_name = "base.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Campaigns"
        return context


class CampaignAPIView(APIView):
    def get(self, request):
        return Response({"message": "Campaigns API"}, status=status.HTTP_200_OK)
