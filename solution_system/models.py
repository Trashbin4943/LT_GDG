from django.db import models
from django.utils import timezone

class SolutionResult(models.Model):
    """
    [결과 저장] 생성된 상담 솔루션 및 가이드
    - audio_process.SpeakerSegment와 1:1 관계
    """
    
    # === 1. 대상 연결 ===
    segment = models.OneToOneField(
        'audio_process.SpeakerSegment',
        on_delete=models.CASCADE,
        related_name='solution_result',
        primary_key=True
    )

    # === 2. 입력 데이터 기록 (분석 당시의 상황) ===
    # 솔루션 생성의 근거가 되는 데이터들
    input_emotion_label = models.CharField(max_length=50)      # 예: 격분
    input_logical_label = models.CharField(max_length=50)      # 예: COMPLAINT
    input_logical_type = models.CharField(max_length=20)       # 예: NORMAL/SPECIAL
    input_risk_score = models.FloatField(default=0.0)          # 예: 0.85
    input_profanity_category = models.CharField(max_length=50, null=True, blank=True)
    
    # === 3. 생성된 솔루션 (Output) ===
    # ResponseGuide 객체의 내용을 저장
    strategy_title = models.CharField(max_length=200, help_text="대응 전략 제목")
    strategy_description = models.TextField(help_text="전략 상세 설명")
    tone_and_manner = models.CharField(max_length=200, help_text="권장 어조")
    
    # 리스트형 데이터는 JSONField 사용
    required_keywords = models.JSONField(default=list, help_text="필수 키워드")
    prohibited_keywords = models.JSONField(default=list, help_text="금지 키워드")
    solution_scripts = models.JSONField(default=list, help_text="추천 스크립트 목록")
    checkpoints = models.JSONField(default=list, help_text="상담원 체크포인트")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "상담 솔루션 결과"
        db_table = "solution_result"

    def __str__(self):
        return f"Solution for {self.segment_id} ({self.strategy_title})"