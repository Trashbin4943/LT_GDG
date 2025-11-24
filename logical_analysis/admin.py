# logical_analysis/admin.py
from django.contrib import admin
from .models import LogicalResult

@admin.register(LogicalResult)
class LogicalResultAdmin(admin.ModelAdmin):
    list_display = ('segment', 'intent_label', 'profanity_score', 'threat_score', 'empathy_score')
    list_filter = ('is_overlap', 'intent_label')
    search_fields = ('segment__text', 'intent_label')
    readonly_fields = ('segment',)

    def session_id_display(self, obj):
        return obj.segment.recording.session_id
    session_id_display.short_description = "Session ID"

    def short_text(self, obj):
        return obj.segment.text[:40] + "..." if len(obj.segment.text) > 40 else obj.segment.text