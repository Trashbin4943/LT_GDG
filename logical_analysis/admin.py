# logical_analysis/admin.py
from django.contrib import admin
from django.db.models import Count, Q
from .models import ClassificationResult

class ClassificationResultInline(admin.TabularInline):
    model = ClassificationResult
    extra = 0
    readonly_fields = ('created_at', 'timestamp')
    can_delete = False
    fields = ('text', 'label', 'label_type', 'confidence', 'action', 'alert_level', 'created_at')
    ordering = ('created_at',)

@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    list_display = ('session_id_display', 'label', 'action', 'alert_level', 'short_text', 'created_at')
    list_filter = ('alert_level', 'action', 'label_type')
    search_fields = ('text', 'segment__recording__session_id')

    def session_id_display(self, obj):
        return obj.segment.recording.session_id
    session_id_display.short_description = "Session ID"

    def short_text(self, obj):
        return obj.segment.text[:40] + "..." if len(obj.segment.text) > 40 else obj.segment.text