from django.contrib import admin
from django.utils.html import format_html
from .models import CustomerAnalysisResult

@admin.register(CustomerAnalysisResult)
class CustomerAnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 
        'segment_text_preview', 
        'label', 
        'score_risk', 
        'is_profanity', 

        'display_intensity', 
        'display_is_immoral',
        'display_immorality_conf',
        'analyzed_at'
    )
    
    list_filter = (
        'label', 
        'label_type', 
        'is_profanity', 
        'analyzed_at'
    )
    
    search_fields = ('segment__text', 'label')
    
    # 상세 페이지에서 읽기 전용으로 JSON 전체 보기
    readonly_fields = ('classification_probabilities', 'analyzed_at')

    def segment_text_preview(self, obj):
        """본문 미리보기 (너무 길면 자름)"""
        return obj.segment.text[:30] + "..." if obj.segment.text else "-"
    segment_text_preview.short_description = "발화 내용"

    # --- JSON 필드 파싱 함수들 ---

    @admin.display(description='😡 강도 (Intensity)')
    def display_intensity(self, obj):
        probs = obj.classification_probabilities or {}
        
        level = probs.get('metadata_intensity_level', 'LOW')
        raw_val = probs.get('metadata_intensity', 0.0)
        
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            val = 0.0
            
        val_str = f"{val:.2f}" 
        
        if level == 'HIGH':
            color = 'red'
            weight = 'bold'
        elif level == 'MEDIUM':
            color = 'orange'
            weight = 'normal'
        else:
            color = 'green'
            weight = 'normal'
            
        return format_html(
            '<span style="color: {}; font-weight: {};">{} ({})</span>',
            color, weight, level, val_str
        )

    @admin.display(description='👿 비도덕적?', boolean=True)
    def display_is_immoral(self, obj):
        """JSON에서 is_immoral 값을 꺼내서 O/X 아이콘으로 표시"""
        probs = obj.classification_probabilities or {}
        return probs.get('metadata_is_immoral', False)

    @admin.display(description='비도덕 신뢰도')
    def display_immorality_conf(self, obj):
        probs = obj.classification_probabilities or {}
        raw_conf = probs.get('metadata_immorality_confidence', None)
        
        if raw_conf is not None:
            try:
                conf_val = float(raw_conf)
                return f"{conf_val:.2%}"
            except (ValueError, TypeError):
                return str(raw_conf)
        return "-"