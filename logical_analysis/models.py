from django.db import models
from audio_process.models import SpeakerSegment

class LogicalResult(models.Model):
    segment = models.OneToOneField(
        SpeakerSegment,
        on_delete=models.CASCADE,
        related_name='logical_analysis'
    )

    # 기존 음성/행동 분석 메트릭
    speech_speed = models.FloatField(null=True, blank=True)
    pause_duration = models.FloatField(null=True, blank=True)
    is_overlap = models.BooleanField(default=False)

    profanity_score = models.FloatField(null=True, blank=True)
    threat_score = models.FloatField(null=True, blank=True)
    insistence_score = models.FloatField(null=True, blank=True)
    intent_label = models.CharField(max_length=100, null=True, blank=True)

    manual_compliance_score = models.FloatField(null=True, blank=True)
    empathy_score = models.FloatField(null=True, blank=True)
    context_appropriateness = models.FloatField(null=True, blank=True)

    # ClassificationResult에서 사용되던 필드(호환용)
    label = models.CharField(max_length=100, null=True, blank=True)
    label_type = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    probabilities = models.JSONField(null=True, blank=True)
    action = models.CharField(max_length=50, null=True, blank=True)
    alert_level = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logical_results'
        ordering = ['segment__start_time']