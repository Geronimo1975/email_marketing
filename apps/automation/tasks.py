from celery import shared_task
from django.utils import timezone
from django.db.models import Q, F
from datetime import timedelta, datetime
import logging

from .models import (
    AutomationWorkflow,
    WorkflowStep,
    WorkflowSubscriber,
)
from .utils import (
    execute_workflow,
    validate_workflow_conditions,
    get_workflow_performance,
    cleanup_old_workflow_data,
)

logger = logging.getLogger(__name__)


@shared_task
def execute_workflow_task(workflow_id, subscriber_ids=None):
    """
    Execute a workflow asynchronously.
    """
    try:
        workflow = AutomationWorkflow.objects.get(id=workflow_id)

        # Check if workflow is active
        if (
            not workflow.is_active
            or workflow.status != AutomationWorkflow.Status.ACTIVE
        ):
            logger.warning(f"Workflow {workflow_id} is not active, skipping execution")
            return {"error": "Workflow is not active"}

        # Execute workflow
        result = execute_workflow(workflow, subscriber_ids)

        if result.get("success"):
            logger.info(f"Successfully executed workflow {workflow_id}")
            return result
        else:
            logger.error(
                f"Failed to execute workflow {workflow_id}: {result.get('error')}"
            )
            return result

    except AutomationWorkflow.DoesNotExist:
        logger.error(f"Workflow {workflow_id} not found")
        return {"error": "Workflow not found"}
    except Exception as e:
        logger.error(f"Error executing workflow {workflow_id}: {e}")
        return {"error": f"Failed to execute workflow: {str(e)}"}


@shared_task
def process_workflow_triggers():
    """
    Process workflow triggers and start workflows for eligible subscribers.
    """
    try:
        # Get active workflows
        active_workflows = AutomationWorkflow.objects.filter(
            status=AutomationWorkflow.Status.ACTIVE, is_active=True
        )

        processed_count = 0
        for workflow in active_workflows:
            try:
                # Check trigger conditions
                if workflow.trigger_type == "immediate":
                    # Process immediate triggers
                    from apps.subscribers.models import Subscriber

                    eligible_subscribers = Subscriber.objects.filter(
                        status=Subscriber.Status.SUBSCRIBED
                    )

                    for subscriber in eligible_subscribers:
                        if validate_workflow_conditions(workflow, subscriber):
                            # Check if subscriber is already in workflow
                            existing = WorkflowSubscriber.objects.filter(
                                workflow=workflow, subscriber=subscriber
                            ).exists()

                            if not existing:
                                # Trigger workflow for subscriber
                                execute_workflow_task.delay(
                                    workflow.id, [subscriber.id]
                                )
                                processed_count += 1

                elif workflow.trigger_type == "scheduled":
                    # Process scheduled triggers
                    if workflow.trigger_config:
                        import json

                        config = json.loads(workflow.trigger_config)
                        scheduled_time = config.get("scheduled_time")

                        if scheduled_time:
                            scheduled_datetime = datetime.fromisoformat(scheduled_time)
                            if scheduled_datetime <= timezone.now():
                                # Time to execute
                                execute_workflow_task.delay(workflow.id)
                                processed_count += 1

                elif workflow.trigger_type == "event_based":
                    # Process event-based triggers
                    # This would typically be triggered by external events
                    # For now, we'll just log that we're checking
                    logger.debug(
                        f"Checking event-based triggers for workflow {workflow.id}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing triggers for workflow {workflow.id}: {e}"
                )
                continue

        logger.info(f"Processed {processed_count} workflow triggers")
        return {"processed_count": processed_count}

    except Exception as e:
        logger.error(f"Error processing workflow triggers: {e}")
        return {"error": f"Failed to process triggers: {str(e)}"}


@shared_task
def cleanup_completed_workflows():
    """
    Clean up completed workflows and old data.
    """
    try:
        # Clean up old workflow data (older than 30 days)
        cleanup_result = cleanup_old_workflow_data(days=30)

        if cleanup_result.get("success"):
            logger.info(
                f"Cleaned up {cleanup_result.get('deleted_records', 0)} old workflow records"
            )
        else:
            logger.error(f"Cleanup failed: {cleanup_result.get('error')}")

        # Mark old completed workflows as archived
        old_completed_workflows = AutomationWorkflow.objects.filter(
            status=AutomationWorkflow.Status.COMPLETED,
            last_executed__lt=timezone.now() - timedelta(days=90),
        )

        archived_count = 0
        for workflow in old_completed_workflows:
            workflow.status = AutomationWorkflow.Status.ARCHIVED
            workflow.save()
            archived_count += 1

        logger.info(f"Archived {archived_count} old completed workflows")
        return {
            "cleaned_records": cleanup_result.get("deleted_records", 0),
            "archived_workflows": archived_count,
        }

    except Exception as e:
        logger.error(f"Error cleaning up workflows: {e}")
        return {"error": f"Failed to cleanup workflows: {str(e)}"}


@shared_task
def update_workflow_metrics():
    """
    Update workflow performance metrics.
    """
    try:
        workflows = AutomationWorkflow.objects.filter(
            status__in=[
                AutomationWorkflow.Status.ACTIVE,
                AutomationWorkflow.Status.PAUSED,
                AutomationWorkflow.Status.COMPLETED,
            ]
        )

        updated_count = 0
        for workflow in workflows:
            try:
                # Get performance data
                performance = get_workflow_performance(workflow)

                if not performance.get("error"):
                    # Update workflow with latest metrics
                    # This could be stored in a separate metrics table
                    # For now, we'll just log the metrics
                    logger.debug(
                        f"Updated metrics for workflow {workflow.id}: {performance}"
                    )
                    updated_count += 1

            except Exception as e:
                logger.error(f"Error updating metrics for workflow {workflow.id}: {e}")
                continue

        logger.info(f"Updated metrics for {updated_count} workflows")
        return {"updated_count": updated_count}

    except Exception as e:
        logger.error(f"Error updating workflow metrics: {e}")
        return {"error": f"Failed to update metrics: {str(e)}"}


@shared_task
def process_workflow_step(workflow_subscriber_id, step_id):
    """
    Process a specific step for a workflow subscriber.
    """
    try:
        workflow_subscriber = WorkflowSubscriber.objects.get(id=workflow_subscriber_id)
        step = WorkflowStep.objects.get(id=step_id)

        # Check if step is active
        if not step.is_active:
            logger.warning(f"Step {step_id} is not active, skipping")
            return {"error": "Step is not active"}

        # Check if subscriber is still active in workflow
        if workflow_subscriber.status != WorkflowSubscriber.Status.ACTIVE:
            logger.warning(
                f"Subscriber {workflow_subscriber_id} is not active in workflow"
            )
            return {"error": "Subscriber is not active in workflow"}

        # Process step based on type
        if step.step_type == "email":
            # Send email
            result = process_email_step(workflow_subscriber, step)
        elif step.step_type == "delay":
            # Handle delay
            result = process_delay_step(workflow_subscriber, step)
        elif step.step_type == "condition":
            # Check conditions
            result = process_condition_step(workflow_subscriber, step)
        elif step.step_type == "action":
            # Perform action
            result = process_action_step(workflow_subscriber, step)
        else:
            result = {"error": f"Unknown step type: {step.step_type}"}

        # Update workflow subscriber
        workflow_subscriber.last_activity = timezone.now()
        workflow_subscriber.save()

        return result

    except WorkflowSubscriber.DoesNotExist:
        logger.error(f"WorkflowSubscriber {workflow_subscriber_id} not found")
        return {"error": "WorkflowSubscriber not found"}
    except WorkflowStep.DoesNotExist:
        logger.error(f"WorkflowStep {step_id} not found")
        return {"error": "WorkflowStep not found"}
    except Exception as e:
        logger.error(f"Error processing workflow step: {e}")
        return {"error": f"Failed to process step: {str(e)}"}


def process_email_step(workflow_subscriber, step):
    """
    Process an email step.
    """
    try:
        # Parse step configuration
        import json

        config = json.loads(step.config) if step.config else {}

        # Get email template and subject
        template_id = config.get("template_id")
        subject = config.get("subject", "Automated Email")
        from_email = config.get("from_email", "noreply@example.com")

        if not template_id:
            return {"error": "No email template specified"}

        # Send email using campaign system
        from apps.campaigns.models import EmailTemplate
        from apps.campaigns.tasks import send_single_email_task

        try:
            template = EmailTemplate.objects.get(id=template_id)

            # Send email
            send_single_email_task.delay(
                template_id=template.id,
                recipient_email=workflow_subscriber.subscriber.email,
                recipient_name=workflow_subscriber.subscriber.first_name,
                subject=subject,
                from_email=from_email,
            )

            # Move to next step
            next_step = get_next_step(workflow_subscriber.workflow, step)
            if next_step:
                workflow_subscriber.current_step = next_step
                workflow_subscriber.save()

            return {"success": True, "message": "Email sent successfully"}

        except EmailTemplate.DoesNotExist:
            return {"error": "Email template not found"}

    except Exception as e:
        return {"error": f"Failed to process email step: {str(e)}"}


def process_delay_step(workflow_subscriber, step):
    """
    Process a delay step.
    """
    try:
        # Calculate delay
        delay_hours = step.delay_hours or 0
        delay_days = step.delay_days or 0
        total_delay_hours = delay_hours + (delay_days * 24)

        if total_delay_hours > 0:
            # Schedule next step execution
            execute_time = timezone.now() + timedelta(hours=total_delay_hours)

            # Schedule task for later execution
            process_workflow_step.apply_async(
                args=[workflow_subscriber.id, step.id], eta=execute_time
            )

            return {
                "success": True,
                "message": f"Delay scheduled for {total_delay_hours} hours",
            }
        else:
            # No delay, move to next step immediately
            next_step = get_next_step(workflow_subscriber.workflow, step)
            if next_step:
                workflow_subscriber.current_step = next_step
                workflow_subscriber.save()

            return {"success": True, "message": "No delay, moving to next step"}

    except Exception as e:
        return {"error": f"Failed to process delay step: {str(e)}"}


def process_condition_step(workflow_subscriber, step):
    """
    Process a condition step.
    """
    try:
        # Parse conditions
        import json

        conditions = json.loads(step.conditions) if step.conditions else []

        # Check conditions
        conditions_met = True
        for condition in conditions:
            if not validate_workflow_conditions(
                workflow_subscriber.workflow, workflow_subscriber.subscriber
            ):
                conditions_met = False
                break

        if conditions_met:
            # Move to next step
            next_step = get_next_step(workflow_subscriber.workflow, step)
            if next_step:
                workflow_subscriber.current_step = next_step
                workflow_subscriber.save()

            return {"success": True, "message": "Conditions met, moving to next step"}
        else:
            # Conditions not met, complete workflow
            workflow_subscriber.status = WorkflowSubscriber.Status.COMPLETED
            workflow_subscriber.completed_at = timezone.now()
            workflow_subscriber.save()

            return {
                "success": True,
                "message": "Conditions not met, workflow completed",
            }

    except Exception as e:
        return {"error": f"Failed to process condition step: {str(e)}"}


def process_action_step(workflow_subscriber, step):
    """
    Process an action step.
    """
    try:
        # Parse step configuration
        import json

        config = json.loads(step.config) if step.config else {}

        action_type = config.get("action_type")

        if action_type == "update_subscriber":
            # Update subscriber data
            field = config.get("field")
            value = config.get("value")

            if field and value:
                setattr(workflow_subscriber.subscriber, field, value)
                workflow_subscriber.subscriber.save()

        elif action_type == "add_tag":
            # Add tag to subscriber
            tag_name = config.get("tag_name")
            if tag_name:
                from apps.subscribers.models import Tag

                tag, created = Tag.objects.get_or_create(name=tag_name)
                workflow_subscriber.subscriber.tags.add(tag)

        elif action_type == "remove_tag":
            # Remove tag from subscriber
            tag_name = config.get("tag_name")
            if tag_name:
                from apps.subscribers.models import Tag

                try:
                    tag = Tag.objects.get(name=tag_name)
                    workflow_subscriber.subscriber.tags.remove(tag)
                except Tag.DoesNotExist:
                    pass

        # Move to next step
        next_step = get_next_step(workflow_subscriber.workflow, step)
        if next_step:
            workflow_subscriber.current_step = next_step
            workflow_subscriber.save()
        else:
            # No more steps, complete workflow
            workflow_subscriber.status = WorkflowSubscriber.Status.COMPLETED
            workflow_subscriber.completed_at = timezone.now()
            workflow_subscriber.save()

        return {"success": True, "message": "Action completed successfully"}

    except Exception as e:
        return {"error": f"Failed to process action step: {str(e)}"}


def get_next_step(workflow, current_step):
    """
    Get the next step in a workflow.
    """
    try:
        next_steps = workflow.steps.filter(
            order__gt=current_step.order, is_active=True
        ).order_by("order")

        if next_steps.exists():
            return next_steps.first()
        else:
            return None

    except Exception as e:
        logger.error(f"Error getting next step: {e}")
        return None


@shared_task
def monitor_workflow_health():
    """
    Monitor workflow health and handle stuck workflows.
    """
    try:
        # Find stuck workflows (active for more than 24 hours)
        stuck_workflows = WorkflowSubscriber.objects.filter(
            status=WorkflowSubscriber.Status.ACTIVE,
            started_at__lt=timezone.now() - timedelta(hours=24),
        )

        stuck_count = 0
        for workflow_subscriber in stuck_workflows:
            try:
                # Mark as failed
                workflow_subscriber.status = WorkflowSubscriber.Status.FAILED
                workflow_subscriber.save()
                stuck_count += 1

                logger.warning(
                    f"Marked stuck workflow subscriber {workflow_subscriber.id} as failed"
                )

            except Exception as e:
                logger.error(
                    f"Error handling stuck workflow subscriber {workflow_subscriber.id}: {e}"
                )
                continue

        logger.info(f"Handled {stuck_count} stuck workflow subscribers")
        return {"stuck_count": stuck_count}

    except Exception as e:
        logger.error(f"Error monitoring workflow health: {e}")
        return {"error": f"Failed to monitor workflow health: {str(e)}"}
