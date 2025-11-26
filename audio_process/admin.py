from django.contrib import admin
from django.utils.html import format_html
from .models import CallRecording, SpeakerSegment

class SpeakerSegmentInline(admin.TabularInline):
    model = SpeakerSegment
    extra = 0
    fields = ('speaker_label', 'time_range', 'text', 'emotion_label','emotion_confidence')
    readonly_fields = ('time_range',)
    can_delete = False

    def time_range(self, obj):
        start = obj.start_time if obj.start_time is not None else 0.0
        end = obj.end_time if obj.end_time is not None else 0.0
        return f"{start:.1f}s ~ {end:.1f}s"
    time_range.short_description = "시간 구간"

@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'file_name', 'uploader', 'created_at', 'duration', 'processed', 'audio_file_link')
    list_filter = ('processed', 'created_at', 'uploader')
    search_fields = ('session_id', 'file_name', 'uploader__username', 'uploader__korean_name')
    readonly_fields = ('session_id', 'created_at', 'duration', 'audio_file_link')
    inlines = [SpeakerSegmentInline]

    def audio_file_link(self, obj):
        if obj.audio_file:
            return format_html('<a href="{}" target="_blank">오디오 파일 열기</a>', obj.audio_file.url)
        return "파일 없음"
    audio_file_link.short_description = "오디오 파일"

