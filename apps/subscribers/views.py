"""
Views for subscribers app.
"""

from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.response import Response

# Simple placeholder views - these would be expanded with proper functionality
def subscriber_list(request):
    """Simple view for subscriber list."""
    return render(request, 'admin/index.html')