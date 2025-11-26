from django.db import models
from django.utils import timezone

class CustomerAnalysisResult(models.Model):
    """[고객 발화 분석 결과]
    - audio_process앱의 SpeakerSegment별로 저장됩니다.
    """

    segment = models.OneToOneField(
        'audio_process.SpeakerSegment',
        on_delete=models.CASCADE,
        related_name='customer_analysis',
        primary_key=True
    )

    # --- Classification & Profanity ---
    label = models.CharField(max_length=50) # 예: threat
    label_type = models.CharField(max_length=20) # NORMAL / SPECIAL
    classification_confidence = models.FloatField(default=0.0)
    
    classification_probabilities = models.JSONField(default=dict, blank=True)

    is_profanity = models.BooleanField(default=False)
    profanity_category = models.CharField(max_length=50, null=True, blank=True)
    profanity_method = models.CharField(max_length=50, null=True, blank=True)

    # --- Risk Scores (쿼리용 Flatten Fields) ---
    score_risk = models.FloatField(default=0.0, help_text="Turn 단위 종합 리스크 점수")
    score_profanity = models.FloatField(default=0.0)
    score_threat = models.FloatField(default=0.0)
    score_unreasonable_demand = models.FloatField(default=0.0)
    
    score_sexual_harassment = models.FloatField(default=0.0)
    score_hate_speech = models.FloatField(default=0.0)
    score_repetition = models.FloatField(default=0.0)

    # --- Details (Flexible Data) ---
    extracted_features = models.JSONField(default=dict, blank=True) # 키워드 등
    feature_scores_extra = models.JSONField(default=dict, blank=True) # 기타 점수
    
    analyzed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "고객 분석 결과"
        db_table = "customer_analysis_results"
    
    def __str__(self):
        return f"Analysis(Label={self.label}) for Segment {self.segment_id}"
    
