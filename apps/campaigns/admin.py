from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.http import JsonResponse
from .models import (
    EmailTemplate, EmailCampaign, CampaignRecipient,
    CampaignVariant, CampaignSchedule
)


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = [
        'status', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
        'mailgun_message_id', 'bounce_reason'
    ]
    fields = [
        'contact', 'status', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at'
    ]

    def has_add_permission(self, request, obj=None):
        return False


class CampaignVariantInline(admin.TabularInline):
    model = CampaignVariant
    extra = 0
    readonly_fields = ['open_rate_display', 'click_rate_display', 'conversion_rate_display']

    def open_rate_display(self, obj):
        if obj.pk:
            return f"{obj.open_rate:.1f}%"
        return "-"
    open_rate_display.short_description = 'Öffnungsrate'

    def click_rate_display(self, obj):
        if obj.pk:
            return f"{obj.click_rate:.1f}%"
        return "-"
    click_rate_display.short_description = 'Klickrate'

    def conversion_rate_display(self, obj):
        if obj.pk:
            return f"{obj.conversion_rate:.1f}%"
        return "-"
    conversion_rate_display.short_description = 'Konversionsrate'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'template_type', 'service_type', 'times_used_display',
        'avg_performance_display', 'is_active', 'created_at'
    ]
    list_filter = ['template_type', 'service_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'subject']
    readonly_fields = [
        'times_used', 'avg_open_rate', 'avg_click_rate',
        'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Template Informationen', {
            'fields': (
                'name',
                'description',
                ('template_type', 'service_type'),
                'is_active'
            )
        }),
        ('E-Mail Inhalt', {
            'fields': (
                'subject',
                'from_name',
                'html_content',
                'text_content',
            )
        }),
        ('Dateien & Variablen', {
            'fields': (
                'html_file',
                'thumbnail',
                'variables',
            ),
            'classes': ('collapse',)
        }),
        ('Performance Statistiken', {
            'fields': (
                'times_used',
                ('avg_open_rate', 'avg_click_rate'),
            ),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': (
                'created_by',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )

    def times_used_display(self, obj):
        if obj.times_used > 0:
            url = reverse('admin:campaigns_emailcampaign_changelist')
            return format_html(
                '<a href="{}?template__id__exact={}">{} mal</a>',
                url, obj.id, obj.times_used
            )
        return '0 mal'
    times_used_display.short_description = 'Verwendungen'

    def avg_performance_display(self, obj):
        if obj.avg_open_rate > 0 or obj.avg_click_rate > 0:
            return format_html(
                'Öffnung: <strong>{:.1f}%</strong><br>Klick: <strong>{:.1f}%</strong>',
                obj.avg_open_rate, obj.avg_click_rate
            )
        return 'Keine Daten'
    avg_performance_display.short_description = 'Durchschnittliche Performance'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'status_display', 'campaign_type', 'priority_display',
        'performance_display', 'sent_at', 'created_by'
    ]
    list_filter = [
        'status', 'campaign_type', 'priority', 'created_at', 'sent_at',
        'template__template_type'
    ]
    search_fields = ['name', 'description', 'subject']
    readonly_fields = [
        'total_recipients', 'emails_sent', 'emails_delivered', 'emails_bounced',
        'emails_opened', 'emails_clicked', 'unsubscribes', 'complaints',
        'quote_requests', 'phone_calls', 'website_visits',
        'open_rate_display', 'click_rate_display', 'conversion_rate_display',
        'mailgun_campaign_id', 'created_at', 'updated_at', 'sent_at'
    ]

    fieldsets = (
        ('Kampagnen Details', {
            'fields': (
                'name',
                'description',
                ('campaign_type', 'priority'),
                'status',
            )
        }),
        ('E-Mail Inhalt', {
            'fields': (
                'template',
                'subject',
                ('from_name', 'from_email'),
                'reply_to',
                'html_content',
                'text_content',
            )
        }),
        ('Targeting & Listen', {
            'fields': (
                'email_lists',
                'target_business_types',
                'target_districts',
            )
        }),
        ('Zeitplanung', {
            'fields': (
                'send_at',
                'timezone',
            ),
            'classes': ('collapse',)
        }),
        ('A/B Testing', {
            'fields': (
                'ab_test_percentage',
                'ab_winner_criteria',
                'ab_test_duration',
            ),
            'classes': ('collapse',)
        }),
        ('Tracking Einstellungen', {
            'fields': (
                ('track_opens', 'track_clicks'),
            ),
            'classes': ('collapse',)
        }),
        ('Performance Statistiken', {
            'fields': (
                ('total_recipients', 'emails_sent', 'emails_delivered'),
                ('emails_bounced', 'emails_opened', 'emails_clicked'),
                ('unsubscribes', 'complaints'),
                ('quote_requests', 'phone_calls', 'website_visits'),
                ('open_rate_display', 'click_rate_display', 'conversion_rate_display'),
            ),
            'classes': ('collapse',)
        }),
        ('Integration & Metadaten', {
            'fields': (
                'mailgun_campaign_id',
                'created_by',
                ('created_at', 'updated_at', 'sent_at'),
            ),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['email_lists']
    inlines = [CampaignVariantInline, CampaignRecipientInline]

    actions = ['duplicate_campaign', 'send_test_email']

    def status_display(self, obj):
        status_colors = {
            'draft': '#6c757d',
            'scheduled': '#ffc107',
            'sending': '#17a2b8',
            'sent': '#28a745',
            'paused': '#fd7e14',
            'cancelled': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def priority_display(self, obj):
        priority_colors = {
            'low': '#6c757d',
            'normal': '#28a745',
            'high': '#ffc107',
            'urgent': '#dc3545',
        }
        color = priority_colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Priorität'

    def performance_display(self, obj):
        if obj.emails_delivered > 0:
            return format_html(
                'Öffnung: <strong>{:.1f}%</strong><br>'
                'Klick: <strong>{:.1f}%</strong><br>'
                'Konversion: <strong>{:.1f}%</strong>',
                obj.open_rate, obj.click_rate, obj.conversion_rate
            )
        return 'Noch nicht gesendet'
    performance_display.short_description = 'Performance'

    def open_rate_display(self, obj):
        return f"{obj.open_rate:.1f}%"
    open_rate_display.short_description = 'Öffnungsrate'

    def click_rate_display(self, obj):
        return f"{obj.click_rate:.1f}%"
    click_rate_display.short_description = 'Klickrate'

    def conversion_rate_display(self, obj):
        return f"{obj.conversion_rate:.1f}%"
    conversion_rate_display.short_description = 'Konversionsrate'

    def duplicate_campaign(self, request, queryset):
        """Duplicate selected campaigns"""
        for campaign in queryset:
            # Create a copy of the campaign
            campaign.pk = None
            campaign.name = f"{campaign.name} (Kopie)"
            campaign.status = 'draft'
            campaign.emails_sent = 0
            campaign.emails_delivered = 0
            campaign.emails_bounced = 0
            campaign.emails_opened = 0
            campaign.emails_clicked = 0
            campaign.unsubscribes = 0
            campaign.complaints = 0
            campaign.sent_at = None
            campaign.mailgun_campaign_id = ''
            campaign.save()

        count = queryset.count()
        self.message_user(request, f'{count} Kampagne(n) erfolgreich dupliziert.')
    duplicate_campaign.short_description = 'Ausgewählte Kampagnen duplizieren'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:campaign_id>/preview/',
                self.admin_site.admin_view(self.preview_campaign),
                name='campaigns_emailcampaign_preview'
            ),
            path(
                '<int:campaign_id>/send/',
                self.admin_site.admin_view(self.send_campaign),
                name='campaigns_emailcampaign_send'
            ),
        ]
        return custom_urls + urls

    def preview_campaign(self, request, campaign_id):
        """Preview campaign content"""
        campaign = EmailCampaign.objects.get(id=campaign_id)
        context = {
            'campaign': campaign,
            'html_content': campaign.html_content,
            'title': f'Vorschau: {campaign.name}'
        }
        return render(request, 'admin/campaigns/preview.html', context)

    def send_campaign(self, request, campaign_id):
        """Send campaign interface"""
        campaign = EmailCampaign.objects.get(id=campaign_id)

        if request.method == 'POST':
            if campaign.can_send():
                # Here you would trigger the Celery task to send the campaign
                # send_campaign_task.delay(campaign_id)
                messages.success(request, f'Kampagne "{campaign.name}" wurde zum Versand eingeplant.')
                return redirect('admin:campaigns_emailcampaign_changelist')
            else:
                messages.error(request, 'Kampagne kann nicht gesendet werden.')

        context = {
            'campaign': campaign,
            'target_contacts': campaign.get_target_contacts(),
            'title': f'Kampagne senden: {campaign.name}'
        }
        return render(request, 'admin/campaigns/send.html', context)


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = [
        'campaign', 'contact', 'status_display', 'sent_at', 'delivered_at',
        'opened_at', 'clicked_at'
    ]
    list_filter = [
        'status', 'campaign__name', 'sent_at', 'delivered_at'
    ]
    search_fields = [
        'contact__email', 'contact__company_name', 'campaign__name'
    ]
    readonly_fields = [
        'mailgun_message_id', 'personalized_subject', 'personalized_content',
        'sent_at', 'delivered_at', 'bounced_at', 'opened_at', 'clicked_at',
        'unsubscribed_at', 'created_at', 'updated_at'
    ]

    def status_display(self, obj):
        status_colors = {
            'pending': '#6c757d',
            'sent': '#17a2b8',
            'delivered': '#28a745',
            'bounced': '#dc3545',
            'failed': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(CampaignSchedule)
class CampaignScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'campaign', 'frequency', 'start_date', 'next_run_display',
        'is_active'
    ]
    list_filter = ['frequency', 'is_active', 'start_date']
    readonly_fields = ['last_run', 'next_run']

    def next_run_display(self, obj):
        if obj.next_run:
            return obj.next_run.strftime('%d.%m.%Y %H:%M')
        return 'Nicht geplant'
    next_run_display.short_description = 'Nächste Ausführung'