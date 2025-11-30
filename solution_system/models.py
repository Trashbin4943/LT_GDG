from django.db import models
from django.utils import timezone

class SolutionResult(models.Model):
    segment = models.OneToOneField(
        'audio_process.SpeakerSegment', 
        on_delete=models.CASCADE, 
        related_name='solution_result',
        primary_key=True
    )
    
    strategy_title = models.CharField(max_length=100, help_text="대응 전략 제목 (예: 격앙된 고객 진정 유도)")
    strategy_description = models.TextField(help_text="상세 대응 가이드")

    tone_and_manner = models.CharField(max_length=100, help_text="권장 목소리 톤 (예: 차분하고 낮은 톤)")
    
    solution_scripts = models.JSONField(default=list, help_text="실제 응대 스크립트 리스트")
    checkpoints = models.JSONField(default=list, help_text="상담 시 유의사항 리스트")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'solution_results'
        verbose_name = '상담 솔루션'

    def __str__(self):
        return f"Solution for Segment {self.segment_id} : {self.strategy_title}"