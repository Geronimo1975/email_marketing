"""
Views for integrations app.
"""

import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .services import (
    MailgunService, OdooService, validate_webhook_signature,
    process_mailgun_webhook
)
from .models import WebhookLog, Integration

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MailgunWebhookView(View):
    """Handle Mailgun webhook events."""

    def post(self, request):
        try:
            # Verify webhook signature
            if not validate_webhook_signature(request, 'mailgun'):
                logger.warning("Invalid Mailgun webhook signature")
                return HttpResponse(status=401)

            # Parse webhook data
            webhook_data = json.loads(request.body.decode('utf-8'))

            # Log the webhook request
            webhook_log = WebhookLog.objects.create(
                webhook_endpoint_id=1,  # You would get this from URL or config
                request_id=webhook_data.get('event-data', {}).get('id', ''),
                status=WebhookLog.Status.SUCCESS,
                headers=dict(request.headers),
                payload=webhook_data,
                signature=request.POST.get('signature', ''),
            )

            # Process the webhook
            success = process_mailgun_webhook(webhook_data)

            if success:
                webhook_log.status = WebhookLog.Status.SUCCESS
                webhook_log.response_status = 200
            else:
                webhook_log.status = WebhookLog.Status.FAILED
                webhook_log.response_status = 400

            webhook_log.save()

            return HttpResponse(status=200 if success else 400)

        except Exception as e:
            logger.error(f"Error processing Mailgun webhook: {e}")
            return HttpResponse(status=500)


@method_decorator(csrf_exempt, name='dispatch')
class OdooWebhookView(View):
    """Handle Odoo webhook events."""

    def post(self, request):
        try:
            webhook_data = json.loads(request.body.decode('utf-8'))

            # Log the webhook request
            WebhookLog.objects.create(
                webhook_endpoint_id=2,  # You would get this from URL or config
                request_id=webhook_data.get('id', ''),
                status=WebhookLog.Status.SUCCESS,
                headers=dict(request.headers),
                payload=webhook_data,
                response_status=200
            )

            # Process Odoo webhook (implement based on your needs)
            # This might update subscriber data from Odoo changes

            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error processing Odoo webhook: {e}")
            return HttpResponse(status=500)


class SyncOdooContactsView(APIView):
    """API endpoint to sync contacts from Odoo."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get or create Odoo integration
            integration = Integration.objects.filter(
                team=request.user.teams.first(),  # Assuming user belongs to a team
                provider=Integration.Provider.ODOO,
                status=Integration.Status.ACTIVE
            ).first()

            if not integration:
                return Response(
                    {'error': 'Odoo integration not configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create sync job
            from .tasks import sync_odoo_contacts
            task = sync_odoo_contacts.delay(integration.id)

            return Response({
                'message': 'Sync job started',
                'task_id': task.id
            })

        except Exception as e:
            logger.error(f"Error starting Odoo sync: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidateEmailView(APIView):
    """API endpoint to validate email addresses."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Email address required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            mailgun_service = MailgunService()
            validation_result = mailgun_service.validate_email(email)

            return Response({
                'email': email,
                'is_valid': validation_result.get('is_valid', False),
                'reason': validation_result.get('reason', ''),
                'risk': validation_result.get('risk', 'unknown')
            })

        except Exception as e:
            logger.error(f"Email validation error: {e}")
            return Response(
                {'error': 'Validation service unavailable'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class SuppressionListView(APIView):
    """API endpoint to manage Mailgun suppression lists."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get suppression list."""
        suppression_type = request.query_params.get('type', 'bounces')

        try:
            mailgun_service = MailgunService()
            suppressions = mailgun_service.get_suppressions(suppression_type)

            return Response({
                'type': suppression_type,
                'count': len(suppressions),
                'items': suppressions
            })

        except Exception as e:
            logger.error(f"Error fetching suppressions: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Add email to suppression list."""
        email = request.data.get('email')
        suppression_type = request.data.get('type', 'bounces')
        reason = request.data.get('reason', '')

        if not email:
            return Response(
                {'error': 'Email address required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            mailgun_service = MailgunService()
            result = mailgun_service.add_to_suppression(
                email, suppression_type, reason
            )

            return Response({
                'message': 'Email added to suppression list',
                'result': result
            })

        except Exception as e:
            logger.error(f"Error adding to suppression list: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """Remove email from suppression list."""
        email = request.query_params.get('email')
        suppression_type = request.query_params.get('type', 'bounces')

        if not email:
            return Response(
                {'error': 'Email address required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            mailgun_service = MailgunService()
            success = mailgun_service.remove_from_suppression(
                email, suppression_type
            )

            if success:
                return Response({'message': 'Email removed from suppression list'})
            else:
                return Response(
                    {'error': 'Email not found in suppression list'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Error removing from suppression list: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )