from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import EmailEvent, CampaignReport, ContactActivity, HamburgBusinessReport


@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_type_display', 'recipient_email', 'campaign_link',
        'timestamp_display', 'link_type', 'business_hour_display',
        'is_mobile_device', 'city'
    ]
    list_filter = [
        'event_type', 'timestamp', 'link_type', 'business_hour',
        'is_mobile_device', 'city', 'campaign__name'
    ]
    search_fields = [
        'recipient_email', 'mailgun_message_id', 'url',
        'contact__company_name', 'campaign__name'
    ]
    readonly_fields = [
        'mailgun_message_id', 'mailgun_event_id', 'timestamp',
        'business_hour', 'is_mobile_device', 'raw_data', 'created_at'
    ]
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Event Information', {
            'fields': (
                'event_type',
                'timestamp',
                ('recipient_email', 'contact'),
                ('campaign', 'campaign_recipient'),
            )
        }),
        ('Link Details', {
            'fields': (
                'url',
                'link_type',
            ),
            'classes': ('collapse',)
        }),
        ('Device & Location', {
            'fields': (
                ('user_agent', 'ip_address'),
                ('device_type', 'client_name', 'client_os'),
                ('country', 'region', 'city'),
                ('business_hour', 'is_mobile_device'),
            ),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': (
                'bounce_reason',
                'bounce_code',
                'error_message',
            ),
            'classes': ('collapse',)
        }),
        ('Technical Data', {
            'fields': (
                ('mailgun_message_id', 'mailgun_event_id'),
                'raw_data',
                'created_at',
            ),
            'classes': ('collapse',)
        }),
    )

    def event_type_display(self, obj):
        colors = {
            'delivered': '#28a745',
            'opened': '#17a2b8',
            'clicked': '#ffc107',
            'unsubscribed': '#fd7e14',
            'complained': '#dc3545',
            'bounced': '#dc3545',
            'failed': '#dc3545',
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_event_type_display()
        )
    event_type_display.short_description = 'Event Typ'

    def campaign_link(self, obj):
        if obj.campaign:
            url = reverse('admin:campaigns_emailcampaign_change', args=[obj.campaign.id])
            return format_html('<a href="{}">{}</a>', url, obj.campaign.name)
        return '-'
    campaign_link.short_description = 'Kampagne'

    def timestamp_display(self, obj):
        return obj.timestamp.strftime('%d.%m.%Y %H:%M')
    timestamp_display.short_description = 'Zeit'

    def business_hour_display(self, obj):
        if obj.business_hour:
            return format_html('<span style="color: green;"> Geschäftszeit</span>')
        return format_html('<span style="color: #6c757d;">Außerhalb</span>')
    business_hour_display.short_description = 'Geschäftszeit'

    def has_add_permission(self, request):
        return False  # Events are created by webhooks only

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'contact', 'campaign', 'campaign_recipient'
        )


@admin.register(CampaignReport)
class CampaignReportAdmin(admin.ModelAdmin):
    list_display = [
        'campaign_link', 'date', 'performance_summary',
        'business_metrics', 'mobile_engagement_rate'
    ]
    list_filter = ['date', 'campaign__name', 'campaign__campaign_type']
    search_fields = ['campaign__name']
    readonly_fields = [
        'open_rate', 'click_rate', 'bounce_rate',
        'business_conversion_rate', 'mobile_engagement_rate',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Kampagne & Datum', {
            'fields': ('campaign', 'date')
        }),
        ('E-Mail Statistiken', {
            'fields': (
                ('emails_sent', 'emails_delivered'),
                ('emails_bounced', 'emails_failed'),
                ('unique_opens', 'total_opens'),
                ('unique_clicks', 'total_clicks'),
            )
        }),
        ('Business Metriken', {
            'fields': (
                ('quote_request_clicks', 'phone_call_clicks'),
                'website_visits',
                'business_conversion_rate',
            )
        }),
        ('Engagement Analyse', {
            'fields': (
                ('business_hour_opens', 'mobile_opens'),
                'mobile_engagement_rate',
                ('unsubscribes', 'complaints'),
            )
        }),
        ('Performance Raten', {
            'fields': (
                ('open_rate', 'click_rate', 'bounce_rate'),
            ),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': (
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )

    def campaign_link(self, obj):
        url = reverse('admin:campaigns_emailcampaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)
    campaign_link.short_description = 'Kampagne'

    def performance_summary(self, obj):
        return format_html(
            'Öffnung: <strong>{:.1f}%</strong><br>'
            'Klick: <strong>{:.1f}%</strong><br>'
            'Bounce: <strong>{:.1f}%</strong>',
            obj.open_rate, obj.click_rate, obj.bounce_rate
        )
    performance_summary.short_description = 'Performance'

    def business_metrics(self, obj):
        return format_html(
            'Angebote: <strong>{}</strong><br>'
            'Anrufe: <strong>{}</strong><br>'
            'Konversion: <strong>{:.1f}%</strong>',
            obj.quote_request_clicks, obj.phone_call_clicks, obj.business_conversion_rate
        )
    business_metrics.short_description = 'Business Metriken'

    def has_add_permission(self, request):
        return False  # Reports are generated automatically


@admin.register(ContactActivity)
class ContactActivityAdmin(admin.ModelAdmin):
    list_display = [
        'contact_link', 'engagement_score_display', 'lead_score_display',
        'performance_summary', 'business_actions', 'last_activity'
    ]
    list_filter = [
        'most_interested_service', 'primarily_mobile', 'prefers_business_hours',
        'contact__business_type', 'contact__hamburg_district'
    ]
    search_fields = [
        'contact__email', 'contact__company_name', 'contact__first_name', 'contact__last_name'
    ]
    readonly_fields = [
        'open_rate', 'click_rate', 'business_engagement_rate',
        'updated_at'
    ]

    fieldsets = (
        ('Kontakt', {
            'fields': ('contact',)
        }),
        ('E-Mail Engagement', {
            'fields': (
                ('emails_received', 'emails_opened', 'emails_clicked'),
                ('open_rate', 'click_rate'),
                ('first_opened', 'last_opened'),
                ('first_clicked', 'last_clicked'),
            )
        }),
        ('Business Aktionen', {
            'fields': (
                ('quote_requests', 'phone_clicks', 'service_page_visits'),
                'business_engagement_rate',
            )
        }),
        ('Scores & Präferenzen', {
            'fields': (
                ('engagement_score', 'lead_score'),
                'most_interested_service',
                ('preferred_send_time', 'preferred_day_of_week'),
                ('primarily_mobile', 'prefers_business_hours'),
            )
        }),
        ('Metadaten', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['update_lead_scores']

    def contact_link(self, obj):
        url = reverse('admin:subscribers_emailcontact_change', args=[obj.contact.id])
        return format_html('<a href="{}">{}</a>', url, obj.contact.full_name)
    contact_link.short_description = 'Kontakt'

    def engagement_score_display(self, obj):
        score = obj.engagement_score
        if score > 0.7:
            color = '#28a745'  # Green
        elif score > 0.4:
            color = '#ffc107'  # Yellow
        else:
            color = '#dc3545'  # Red

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}</span>',
            color, score
        )
    engagement_score_display.short_description = 'Engagement Score'

    def lead_score_display(self, obj):
        score = obj.lead_score
        if score > 80:
            icon = '=%'
            color = '#dc3545'
        elif score > 60:
            icon = 'P'
            color = '#ffc107'
        elif score > 40:
            icon = '=d'
            color = '#28a745'
        else:
            icon = '=¤'
            color = '#6c757d'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.0f}</span>',
            color, icon, score
        )
    lead_score_display.short_description = 'Lead Score'

    def performance_summary(self, obj):
        return format_html(
            'Öffnung: <strong>{:.1f}%</strong><br>'
            'Klick: <strong>{:.1f}%</strong>',
            obj.open_rate, obj.click_rate
        )
    performance_summary.short_description = 'Performance'

    def business_actions(self, obj):
        return format_html(
            'Angebote: <strong>{}</strong><br>'
            'Anrufe: <strong>{}</strong><br>'
            'Service Besuche: <strong>{}</strong>',
            obj.quote_requests, obj.phone_clicks, obj.service_page_visits
        )
    business_actions.short_description = 'Business Aktionen'

    def last_activity(self, obj):
        if obj.last_opened and obj.last_clicked:
            last = max(obj.last_opened, obj.last_clicked)
            action = 'geklickt' if obj.last_clicked > obj.last_opened else 'geöffnet'
        elif obj.last_opened:
            last = obj.last_opened
            action = 'geöffnet'
        elif obj.last_clicked:
            last = obj.last_clicked
            action = 'geklickt'
        else:
            return 'Keine Aktivität'

        return format_html(
            '{}<br><small>{}</small>',
            last.strftime('%d.%m.%Y %H:%M'), action
        )
    last_activity.short_description = 'Letzte Aktivität'

    def update_lead_scores(self, request, queryset):
        """Update lead scores for selected contacts"""
        for activity in queryset:
            activity.update_lead_score()
        count = queryset.count()
        self.message_user(request, f'Lead Scores für {count} Kontakte aktualisiert.')
    update_lead_scores.short_description = 'Lead Scores aktualisieren'

    def has_add_permission(self, request):
        return False  # Activities are created automatically


@admin.register(HamburgBusinessReport)
class HamburgBusinessReportAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_district_contacts', 'conversion_rate_display',
        'lead_generation_summary', 'top_performing_district'
    ]
    list_filter = ['date']
    readonly_fields = [
        'total_district_contacts', 'conversion_rate',
        'created_at'
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Berichtsdatum', {
            'fields': ('date',)
        }),
        ('Kontakte nach Bezirk', {
            'fields': (
                ('altona_contacts', 'bergedorf_contacts'),
                ('eimsbuettel_contacts', 'harburg_contacts'),
                ('mitte_contacts', 'nord_contacts'),
                'wandsbek_contacts',
                'total_district_contacts',
            )
        }),
        ('Engagement nach Geschäftstyp', {
            'fields': (
                ('office_engagement', 'retail_engagement'),
                ('medical_engagement', 'restaurant_engagement'),
            )
        }),
        ('Lead Generation', {
            'fields': (
                ('total_quote_requests', 'total_phone_calls'),
                'hot_leads_generated',
                'conversion_rate',
            )
        }),
        ('Zeitliche Erkenntnisse', {
            'fields': (
                ('best_send_hour', 'best_send_day'),
            )
        }),
        ('Metadaten', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def conversion_rate_display(self, obj):
        rate = obj.conversion_rate
        if rate > 5:
            color = '#28a745'
        elif rate > 2:
            color = '#ffc107'
        else:
            color = '#dc3545'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    conversion_rate_display.short_description = 'Konversionsrate'

    def lead_generation_summary(self, obj):
        return format_html(
            'Angebote: <strong>{}</strong><br>'
            'Anrufe: <strong>{}</strong><br>'
            'Hot Leads: <strong>{}</strong>',
            obj.total_quote_requests, obj.total_phone_calls, obj.hot_leads_generated
        )
    lead_generation_summary.short_description = 'Lead Generation'

    def top_performing_district(self, obj):
        districts = {
            'Altona': obj.altona_contacts,
            'Bergedorf': obj.bergedorf_contacts,
            'Eimsbüttel': obj.eimsbuettel_contacts,
            'Harburg': obj.harburg_contacts,
            'Hamburg-Mitte': obj.mitte_contacts,
            'Hamburg-Nord': obj.nord_contacts,
            'Wandsbek': obj.wandsbek_contacts,
        }
        if any(districts.values()):
            top_district = max(districts, key=districts.get)
            return format_html(
                '<strong>{}</strong><br><small>{} Kontakte</small>',
                top_district, districts[top_district]
            )
        return 'Keine Daten'
    top_performing_district.short_description = 'Top Bezirk'

    def has_add_permission(self, request):
        return False  # Reports are generated automatically