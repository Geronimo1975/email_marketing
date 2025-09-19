from django.db.models import Q, Count, Sum, Avg, F, Max, Min
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from .models import (
    AutomationWorkflow,
    WorkflowStep,
    WorkflowSubscriber,
)

User = get_user_model()


def execute_workflow(workflow, subscriber_ids=None):
    """
    Execute a workflow for specific subscribers.
    """
    try:
        # Validate workflow
        if not workflow.is_active:
            return {"error": "Workflow is not active"}

        if workflow.status != AutomationWorkflow.Status.ACTIVE:
            return {"error": "Workflow is not in active status"}

        # Get subscribers
        if subscriber_ids is None:
            # Get all eligible subscribers based on workflow conditions
            from apps.subscribers.models import Subscriber

            subscribers = Subscriber.objects.filter(status=Subscriber.Status.SUBSCRIBED)
        else:
            # Get specific subscribers
            from apps.subscribers.models import Subscriber

            subscribers = Subscriber.objects.filter(
                Q(id__in=subscriber_ids) | Q(email__in=subscriber_ids)
            )

        if not subscribers.exists():
            return {"error": "No eligible subscribers found"}

        # Create workflow subscribers
        workflow_subscribers = []
        for subscriber in subscribers:
            workflow_subscriber, created = WorkflowSubscriber.objects.get_or_create(
                workflow=workflow,
                subscriber=subscriber,
                defaults={
                    "status": WorkflowSubscriber.Status.ACTIVE,
                    "started_at": timezone.now(),
                },
            )
            if created:
                workflow_subscribers.append(workflow_subscriber)

        # Update workflow execution count
        workflow.execution_count += 1
        workflow.last_executed = timezone.now()
        workflow.save()

        return {
            "success": True,
            "subscribers_processed": len(workflow_subscribers),
            "execution_id": f"exec_{workflow.id}_{int(timezone.now().timestamp())}",
        }

    except Exception as e:
        return {"error": f"Failed to execute workflow: {str(e)}"}


def validate_workflow_conditions(workflow, subscriber):
    """
    Validate if a subscriber meets workflow conditions.
    """
    try:
        if not workflow.conditions:
            return True

        import json

        conditions = json.loads(workflow.conditions)

        # Simple condition validation
        # This is a basic implementation - can be extended
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            if not field or not operator:
                continue

            # Get subscriber field value
            subscriber_value = getattr(subscriber, field, None)
            if subscriber_value is None:
                continue

            # Apply condition logic
            if operator == "equals":
                if str(subscriber_value) != str(value):
                    return False
            elif operator == "not_equals":
                if str(subscriber_value) == str(value):
                    return False
            elif operator == "contains":
                if value not in str(subscriber_value):
                    return False
            elif operator == "not_contains":
                if value in str(subscriber_value):
                    return False
            elif operator == "greater_than":
                if not (subscriber_value > float(value)):
                    return False
            elif operator == "less_than":
                if not (subscriber_value < float(value)):
                    return False
            elif operator == "is_empty":
                if subscriber_value:
                    return False
            elif operator == "is_not_empty":
                if not subscriber_value:
                    return False

        return True

    except Exception as e:
        # If validation fails, default to True
        return True


def get_workflow_stats(user):
    """
    Get comprehensive workflow statistics for a user.
    """
    # Get user's workflows
    if user.is_admin:
        workflows = AutomationWorkflow.objects.all()
    else:
        workflows = AutomationWorkflow.objects.filter(
            Q(team__members=user) | Q(created_by=user)
        ).distinct()

    # Basic counts
    total_workflows = workflows.count()
    active_workflows = workflows.filter(status=AutomationWorkflow.Status.ACTIVE).count()
    paused_workflows = workflows.filter(status=AutomationWorkflow.Status.PAUSED).count()
    completed_workflows = workflows.filter(
        status=AutomationWorkflow.Status.COMPLETED
    ).count()

    # Subscriber counts
    workflow_subscribers = WorkflowSubscriber.objects.filter(workflow__in=workflows)
    total_subscribers = workflow_subscribers.count()
    active_subscribers = workflow_subscribers.filter(
        status=WorkflowSubscriber.Status.ACTIVE
    ).count()
    completed_subscribers = workflow_subscribers.filter(
        status=WorkflowSubscriber.Status.COMPLETED
    ).count()
    failed_subscribers = workflow_subscribers.filter(
        status=WorkflowSubscriber.Status.FAILED
    ).count()

    # Performance metrics
    successful_executions = (
        workflows.filter(execution_count__gt=0).aggregate(total=Sum("execution_count"))[
            "total"
        ]
        or 0
    )

    success_rate = 0
    if total_workflows > 0:
        success_rate = (active_workflows / total_workflows) * 100

    completion_rate = 0
    if total_subscribers > 0:
        completion_rate = (completed_subscribers / total_subscribers) * 100

    # Recent activity
    recent_executions = workflows.filter(
        last_executed__gte=timezone.now() - timedelta(days=7)
    ).order_by("-last_executed")[:5]

    recent_data = []
    for workflow in recent_executions:
        recent_data.append(
            {
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "last_executed": workflow.last_executed,
                "execution_count": workflow.execution_count,
            }
        )

    # Top performing workflows
    top_workflows = workflows.filter(execution_count__gt=0).order_by(
        "-execution_count"
    )[:5]

    top_data = []
    for workflow in top_workflows:
        top_data.append(
            {
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "execution_count": workflow.execution_count,
                "status": workflow.status,
            }
        )

    return {
        "total_workflows": total_workflows,
        "active_workflows": active_workflows,
        "paused_workflows": paused_workflows,
        "completed_workflows": completed_workflows,
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "completed_subscribers": completed_subscribers,
        "failed_subscribers": failed_subscribers,
        "success_rate": round(success_rate, 2),
        "completion_rate": round(completion_rate, 2),
        "recent_executions": recent_data,
        "top_performing_workflows": top_data,
    }


def get_subscriber_workflows(subscriber):
    """
    Get all workflows for a specific subscriber.
    """
    workflow_subscribers = WorkflowSubscriber.objects.filter(
        subscriber=subscriber
    ).select_related("workflow", "current_step")

    workflows = []
    for ws in workflow_subscribers:
        workflows.append(
            {
                "workflow_id": ws.workflow.id,
                "workflow_name": ws.workflow.name,
                "status": ws.status,
                "current_step": ws.current_step.name if ws.current_step else None,
                "started_at": ws.started_at,
                "completed_at": ws.completed_at,
                "last_activity": ws.last_activity,
            }
        )

    return workflows


def trigger_workflow_for_subscriber(workflow, subscriber):
    """
    Trigger a workflow for a specific subscriber.
    """
    try:
        # Check if subscriber meets conditions
        if not validate_workflow_conditions(workflow, subscriber):
            return {"error": "Subscriber does not meet workflow conditions"}

        # Create or update workflow subscriber
        workflow_subscriber, created = WorkflowSubscriber.objects.get_or_create(
            workflow=workflow,
            subscriber=subscriber,
            defaults={
                "status": WorkflowSubscriber.Status.ACTIVE,
                "started_at": timezone.now(),
            },
        )

        if (
            not created
            and workflow_subscriber.status == WorkflowSubscriber.Status.COMPLETED
        ):
            return {"error": "Subscriber has already completed this workflow"}

        # Start workflow execution
        workflow_subscriber.status = WorkflowSubscriber.Status.ACTIVE
        workflow_subscriber.started_at = timezone.now()
        workflow_subscriber.save()

        return {
            "success": True,
            "workflow_subscriber_id": workflow_subscriber.id,
            "message": "Workflow triggered successfully",
        }

    except Exception as e:
        return {"error": f"Failed to trigger workflow: {str(e)}"}


def pause_workflow(workflow):
    """
    Pause a workflow.
    """
    try:
        workflow.status = AutomationWorkflow.Status.PAUSED
        workflow.save()

        # Pause all active workflow subscribers
        WorkflowSubscriber.objects.filter(
            workflow=workflow, status=WorkflowSubscriber.Status.ACTIVE
        ).update(status=WorkflowSubscriber.Status.PAUSED)

        return {"success": True, "message": "Workflow paused successfully"}

    except Exception as e:
        return {"error": f"Failed to pause workflow: {str(e)}"}


def resume_workflow(workflow):
    """
    Resume a paused workflow.
    """
    try:
        workflow.status = AutomationWorkflow.Status.ACTIVE
        workflow.save()

        # Resume all paused workflow subscribers
        WorkflowSubscriber.objects.filter(
            workflow=workflow, status=WorkflowSubscriber.Status.PAUSED
        ).update(status=WorkflowSubscriber.Status.ACTIVE)

        return {"success": True, "message": "Workflow resumed successfully"}

    except Exception as e:
        return {"error": f"Failed to resume workflow: {str(e)}"}


def get_workflow_performance(workflow):
    """
    Get performance metrics for a specific workflow.
    """
    try:
        # Execution metrics
        total_executions = workflow.execution_count
        successful_executions = WorkflowSubscriber.objects.filter(
            workflow=workflow, status=WorkflowSubscriber.Status.COMPLETED
        ).count()
        failed_executions = WorkflowSubscriber.objects.filter(
            workflow=workflow, status=WorkflowSubscriber.Status.FAILED
        ).count()

        success_rate = 0
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100

        # Subscriber metrics
        workflow_subscribers = WorkflowSubscriber.objects.filter(workflow=workflow)
        total_subscribers = workflow_subscribers.count()
        active_subscribers = workflow_subscribers.filter(
            status=WorkflowSubscriber.Status.ACTIVE
        ).count()
        completed_subscribers = workflow_subscribers.filter(
            status=WorkflowSubscriber.Status.COMPLETED
        ).count()

        completion_rate = 0
        if total_subscribers > 0:
            completion_rate = (completed_subscribers / total_subscribers) * 100

        # Timing metrics
        completed_workflows = workflow_subscribers.filter(
            status=WorkflowSubscriber.Status.COMPLETED, completed_at__isnull=False
        )

        execution_times = []
        for ws in completed_workflows:
            if ws.started_at and ws.completed_at:
                duration = (
                    ws.completed_at - ws.started_at
                ).total_seconds() / 3600  # hours
                execution_times.append(duration)

        average_execution_time = 0
        fastest_execution = 0
        slowest_execution = 0

        if execution_times:
            average_execution_time = sum(execution_times) / len(execution_times)
            fastest_execution = min(execution_times)
            slowest_execution = max(execution_times)

        # Step performance
        steps = workflow.steps.all().order_by("order")
        step_performance = []
        for step in steps:
            step_subscribers = workflow_subscribers.filter(current_step=step)
            step_completed = step_subscribers.filter(
                status=WorkflowSubscriber.Status.COMPLETED
            ).count()
            step_total = step_subscribers.count()

            step_success_rate = 0
            if step_total > 0:
                step_success_rate = (step_completed / step_total) * 100

            step_performance.append(
                {
                    "step_id": step.id,
                    "step_name": step.name,
                    "step_type": step.step_type,
                    "total_subscribers": step_total,
                    "completed_subscribers": step_completed,
                    "success_rate": round(step_success_rate, 2),
                }
            )

        # Recent activity
        recent_activity = workflow_subscribers.filter(
            last_activity__gte=timezone.now() - timedelta(days=7)
        ).order_by("-last_activity")[:10]

        recent_data = []
        for ws in recent_activity:
            recent_data.append(
                {
                    "subscriber_id": ws.subscriber.id,
                    "subscriber_email": ws.subscriber.email,
                    "status": ws.status,
                    "current_step": ws.current_step.name if ws.current_step else None,
                    "last_activity": ws.last_activity,
                }
            )

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 2),
            "total_subscribers": total_subscribers,
            "active_subscribers": active_subscribers,
            "completed_subscribers": completed_subscribers,
            "completion_rate": round(completion_rate, 2),
            "average_execution_time": round(average_execution_time, 2),
            "fastest_execution": round(fastest_execution, 2),
            "slowest_execution": round(slowest_execution, 2),
            "step_performance": step_performance,
            "recent_activity": recent_data,
        }

    except Exception as e:
        return {"error": f"Failed to get workflow performance: {str(e)}"}


def cleanup_old_workflow_data(days=30):
    """
    Clean up old workflow data.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        # Clean up old completed workflow subscribers
        old_completed = WorkflowSubscriber.objects.filter(
            status=WorkflowSubscriber.Status.COMPLETED, completed_at__lt=cutoff_date
        )
        deleted_count = old_completed.count()
        old_completed.delete()

        # Clean up old failed workflow subscribers
        old_failed = WorkflowSubscriber.objects.filter(
            status=WorkflowSubscriber.Status.FAILED, last_activity__lt=cutoff_date
        )
        deleted_count += old_failed.count()
        old_failed.delete()

        return {
            "success": True,
            "deleted_records": deleted_count,
            "message": f"Cleaned up {deleted_count} old workflow records",
        }

    except Exception as e:
        return {"error": f"Failed to cleanup old data: {str(e)}"}


def get_workflow_analytics(user, date_from=None, date_to=None):
    """
    Get workflow analytics for a user.
    """
    try:
        # Get user's workflows
        if user.is_admin:
            workflows = AutomationWorkflow.objects.all()
        else:
            workflows = AutomationWorkflow.objects.filter(
                Q(team__members=user) | Q(created_by=user)
            ).distinct()

        # Apply date filters
        if date_from:
            workflows = workflows.filter(created_at__date__gte=date_from)
        if date_to:
            workflows = workflows.filter(created_at__date__lte=date_to)

        # Time-based metrics
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        executions_today = workflows.filter(last_executed__date=today).count()
        executions_this_week = workflows.filter(
            last_executed__date__gte=week_start
        ).count()
        executions_this_month = workflows.filter(
            last_executed__date__gte=month_start
        ).count()

        # Performance trends
        daily_executions = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = workflows.filter(last_executed__date=date).count()
            daily_executions.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "count": count,
                }
            )

        # Subscriber engagement
        workflow_subscribers = WorkflowSubscriber.objects.filter(workflow__in=workflows)
        engagement_data = {
            "total_subscribers": workflow_subscribers.count(),
            "active_subscribers": workflow_subscribers.filter(
                status=WorkflowSubscriber.Status.ACTIVE
            ).count(),
            "completed_subscribers": workflow_subscribers.filter(
                status=WorkflowSubscriber.Status.COMPLETED
            ).count(),
            "failed_subscribers": workflow_subscribers.filter(
                status=WorkflowSubscriber.Status.FAILED
            ).count(),
        }

        return {
            "executions_today": executions_today,
            "executions_this_week": executions_this_week,
            "executions_this_month": executions_this_month,
            "daily_executions": daily_executions,
            "subscriber_engagement": engagement_data,
        }

    except Exception as e:
        return {"error": f"Failed to get workflow analytics: {str(e)}"}
