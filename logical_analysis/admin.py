from django.contrib import admin
from django.utils.html import format_html
from .models import CustomerAnalysisResult

@admin.register(CustomerAnalysisResult)
class CustomerAnalysisResultAdmin(admin.ModelAdmin):
    # 1. 목록 화면에 보여질 컬럼들
    list_display = (
        'segment_id_display',   # 세그먼트 ID
        'get_segment_text',     # 발화 내용 (미리보기)
        'label_badge',          # 라벨 (뱃지 스타일)
        'label_type',           # NORMAL / SPECIAL
        'colored_risk_score',   # 리스크 점수 (색상 적용)
        'is_profanity',         # 욕설 여부 (아이콘)
        'analyzed_at',          # 분석 시간
    )

    # 2. 우측 사이드바 필터
    list_filter = (
        'label_type',           # 라벨 타입별 보기
        'is_profanity',         # 욕설 여부별 보기
        'label',                # 상세 라벨별 보기
        'analyzed_at',          # 날짜별 보기
    )

    # 3. 검색창 설정 (세그먼트 텍스트로도 검색 가능하게)
    search_fields = (
        'label', 
        'profanity_category', 
        'segment__text'         # 연결된 SpeakerSegment의 텍스트로 검색
    )

    # 4. 상세 페이지 필드 그룹화 (보기 좋게 정리)
    fieldsets = (
        ('기본 정보', {
            'fields': ('segment', 'analyzed_at')
        }),
        ('분석 결과', {
            'fields': (
                'label', 'label_type', 'classification_confidence', 
                'is_profanity', 'profanity_category', 'profanity_method'
            )
        }),
        ('리스크 점수 (Risk Scores)', {
            'fields': (
                'score_risk', 'score_profanity', 'score_threat', 
                'score_unreasonable_demand', 'score_sexual_harassment', 
                'score_hate_speech', 'score_repetition'
            ),
            'classes': ('wide',)
        }),
        ('상세 데이터 (JSON)', {
            'fields': ('classification_probabilities', 'extracted_features', 'feature_scores_extra'),
            'classes': ('collapse',)  # 기본적으로는 접어두기
        }),
    )

    # 5. 읽기 전용 필드 (실수로 수정 방지)
    readonly_fields = ('analyzed_at', 'segment')

    # --- 커스텀 메서드들 (화면을 예쁘게 만들기 위함) ---

    @admin.display(description='세그먼트 ID', ordering='segment__id')
    def segment_id_display(self, obj):
        return f"Segment #{obj.segment.id}"

    @admin.display(description='발화 내용')
    def get_segment_text(self, obj):
        """연결된 세그먼트의 텍스트를 가져와서 보여줍니다."""
        text = obj.segment.text
        if len(text) > 30:
            return text[:30] + "..."
        return text

    @admin.display(description='리스크 점수', ordering='score_risk')
    def colored_risk_score(self, obj):
        """점수가 높으면 빨간색으로 표시합니다."""
        score = obj.score_risk
        if score >= 0.7:
            color = 'red'
            weight = 'bold'
        elif score >= 0.4:
            color = 'orange'
            weight = 'bold'
        else:
            color = 'green'
            weight = 'normal'
        return format_html('<span style="color: {}; font-weight: {};">{}</span>', color, weight, score)

    @admin.display(description='라벨')
    def label_badge(self, obj):
        """라벨을 좀 더 눈에 띄게 표시합니다."""
        if obj.label_type == 'SPECIAL':
            return format_html('<span style="background-color: #ffcccc; padding: 3px 6px; border-radius: 4px;">{}</span>', obj.label)
        return obj.label