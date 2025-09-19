from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
import csv
from .models import EmailList, EmailContact, ContactImport, ContactTag, ContactNote


@admin.register(EmailList)
class EmailListAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'list_type', 'contact_count_display', 'subscribed_count_display',
        'created_by', 'created_at', 'is_active'
    ]
    list_filter = ['list_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Grundinformationen', {
            'fields': ('name', 'description', 'list_type', 'is_active')
        }),
        ('Metadaten', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def contact_count_display(self, obj):
        count = obj.contact_count
        url = reverse('admin:subscribers_emailcontact_changelist')
        return format_html(
            '<a href="{}?email_lists__id__exact={}">{} Kontakte</a>',
            url, obj.id, count
        )
    contact_count_display.short_description = 'Kontakte'

    def subscribed_count_display(self, obj):
        count = obj.subscribed_count
        return format_html('<strong>{}</strong>', count)
    subscribed_count_display.short_description = 'Abonniert'

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailContact)
class EmailContactAdmin(admin.ModelAdmin):
    list_display = [
        'full_name_display', 'email', 'company_name', 'business_type_display',
        'hamburg_district', 'engagement_score_display', 'is_hot_lead_display',
        'is_subscribed', 'created_at'
    ]
    list_filter = [
        'business_type', 'hamburg_district', 'company_size', 'is_subscribed',
        'is_active', 'gdpr_consent', 'has_current_service', 'created_at'
    ]
    search_fields = [
        'first_name', 'last_name', 'email', 'company_name', 'phone', 'address'
    ]
    readonly_fields = [
        'engagement_score', 'emails_sent', 'emails_opened', 'emails_clicked',
        'last_opened', 'last_clicked', 'created_at', 'updated_at', 'is_hot_lead_display'
    ]

    fieldsets = (
        ('Persönliche Daten', {
            'fields': (
                ('first_name', 'last_name'),
                'email',
                ('position', 'company_name'),
            )
        }),
        ('Geschäftsdaten', {
            'fields': (
                ('business_type', 'company_size'),
                ('hamburg_district', 'postal_code'),
                'address',
                ('phone', 'website'),
            )
        }),
        ('Lead Qualifikation', {
            'fields': (
                'has_current_service',
                'current_service_provider',
                'contract_end_date',
                'interested_services',
                'budget_range',
            ),
            'classes': ('collapse',)
        }),
        ('E-Mail Marketing', {
            'fields': (
                'email_lists',
                ('is_subscribed', 'is_active'),
                ('gdpr_consent', 'consent_date', 'consent_source'),
                'unsubscribed_at',
            )
        }),
        ('Engagement Tracking', {
            'fields': (
                'engagement_score',
                ('emails_sent', 'emails_opened', 'emails_clicked'),
                ('last_opened', 'last_clicked'),
                'is_hot_lead_display',
            ),
            'classes': ('collapse',)
        }),
        ('Integration & Metadaten', {
            'fields': (
                'odoo_contact_id',
                ('source', 'language'),
                'notes',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ['email_lists', 'tags']

    actions = ['export_to_csv', 'mark_as_subscribed', 'mark_as_unsubscribed', 'add_to_list']

    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Name'

    def business_type_display(self, obj):
        return obj.get_business_type_display()
    business_type_display.short_description = 'Geschäftstyp'

    def engagement_score_display(self, obj):
        score = obj.engagement_score
        if score > 0.7:
            color = 'green'
        elif score > 0.4:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}</span>',
            color, score
        )
    engagement_score_display.short_description = 'Engagement'

    def is_hot_lead_display(self, obj):
        if obj.is_hot_lead:
            return format_html(
                '<span style="color: red; font-weight: bold;">=% Hot Lead</span>'
            )
        return '=d Regular'
    is_hot_lead_display.short_description = 'Lead Status'

    def export_to_csv(self, request, queryset):
        """Export selected contacts to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Vorname', 'Nachname', 'E-Mail', 'Firma', 'Geschäftstyp',
            'Hamburg Bezirk', 'Telefon', 'Abonniert', 'Engagement Score'
        ])

        for contact in queryset:
            writer.writerow([
                contact.first_name,
                contact.last_name,
                contact.email,
                contact.company_name,
                contact.get_business_type_display(),
                contact.get_hamburg_district_display(),
                contact.phone,
                'Ja' if contact.is_subscribed else 'Nein',
                contact.engagement_score
            ])

        return response
    export_to_csv.short_description = 'Ausgewählte als CSV exportieren'

    def mark_as_subscribed(self, request, queryset):
        """Mark selected contacts as subscribed"""
        updated = queryset.update(is_subscribed=True, unsubscribed_at=None)
        self.message_user(request, f'{updated} Kontakte als abonniert markiert.')
    mark_as_subscribed.short_description = 'Als abonniert markieren'

    def mark_as_unsubscribed(self, request, queryset):
        """Mark selected contacts as unsubscribed"""
        from django.utils import timezone
        updated = queryset.update(is_subscribed=False, unsubscribed_at=timezone.now())
        self.message_user(request, f'{updated} Kontakte als abgemeldet markiert.')
    mark_as_unsubscribed.short_description = 'Als abgemeldet markieren'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related().prefetch_related('email_lists', 'tags')


@admin.register(ContactImport)
class ContactImportAdmin(admin.ModelAdmin):
    list_display = [
        'filename', 'email_list', 'status', 'success_rate_display',
        'total_rows', 'successful_imports', 'failed_imports',
        'uploaded_by', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'email_list']
    search_fields = ['filename']
    readonly_fields = [
        'total_rows', 'successful_imports', 'failed_imports', 'duplicates_skipped',
        'error_log', 'success_rate_display', 'created_at', 'completed_at'
    ]

    fieldsets = (
        ('Import Details', {
            'fields': ('filename', 'email_list', 'uploaded_by', 'status')
        }),
        ('Statistiken', {
            'fields': (
                'total_rows',
                ('successful_imports', 'failed_imports', 'duplicates_skipped'),
                'success_rate_display',
            )
        }),
        ('Logs & Dateien', {
            'fields': ('error_log', 'processed_file'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Erfolgsrate'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactTag)
class ContactTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'contact_count_display', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['contact_count_display', 'created_at']

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.color, obj.name
        )
    color_display.short_description = 'Farbe'

    def contact_count_display(self, obj):
        count = obj.contact_count
        if count > 0:
            url = reverse('admin:subscribers_emailcontact_changelist')
            return format_html(
                '<a href="{}?tags__id__exact={}">{} Kontakte</a>',
                url, obj.id, count
            )
        return '0 Kontakte'
    contact_count_display.short_description = 'Verwendung'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactNote)
class ContactNoteAdmin(admin.ModelAdmin):
    list_display = ['contact', 'note_preview', 'is_important', 'created_by', 'created_at']
    list_filter = ['is_important', 'created_at', 'created_by']
    search_fields = ['contact__email', 'contact__company_name', 'note']
    readonly_fields = ['created_at']

    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Notiz Vorschau'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Configure admin site headers
admin.site.site_header = "North Cleaning Services - E-Mail Marketing"
admin.site.site_title = "E-Mail Marketing Admin"
admin.site.index_title = "Dashboard"