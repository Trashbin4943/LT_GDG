from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import logging

# 1. 모델 Import
from audio_process.models import SpeakerSegment
from .models import SolutionResult
from .logic.solution_generator import SolutionGenerator
from .schemas import SolutionRequestDTO

logger = logging.getLogger(__name__)

@transaction.atomic
def generate_solution_from_analysis(
    segment: SpeakerSegment,
    emotion_label: str
) -> SolutionResult:
    """
    logical_analysis 결과를 기반으로 솔루션을 자동 생성합니다.
    
    Args:
        segment: SpeakerSegment 객체
        emotion_label: 감정 라벨 (emotion_system에서 가져옴)
    
    Returns:
        SolutionResult 객체
    
    Raises:
        ValueError: 분석 결과가 없는 경우
    """
    # 1. CustomerAnalysisResult 조회
    if not hasattr(segment, 'customer_analysis'):
        raise ValueError(f"Segment {segment.id}에 분석 결과가 없습니다.")
    
    analysis = segment.customer_analysis
    
    # 2. SolutionRequestDTO 생성
    request_data = SolutionRequestDTO(
        session_id=str(segment.session_id.session_id),  # CallRecording.session_id
        turn_index=segment.turn_index,
        text=segment.text or "",
        emotion_label=emotion_label,  # emotion_system에서 가져옴
        logical_label=analysis.label,  # logical_analysis에서 가져옴
        logical_type=analysis.label_type,  # logical_analysis에서 가져옴
        risk_score=analysis.score_risk,  # logical_analysis에서 가져옴
        profanity_category=analysis.profanity_category,  # logical_analysis에서 가져옴
        extracted_keywords=analysis.extracted_features or {}  # logical_analysis에서 가져옴
    )
    
    # 3. 기존 함수 재사용
    return generate_and_save_solution(request_data)

@transaction.atomic
def generate_and_save_solution(request_data: SolutionRequestDTO) -> SolutionResult:
    """
    SolutionRequestDTO를 받아 솔루션을 생성하고 DB에 저장합니다.
    
    Args:
        request_data: 분석 결과를 포함한 요청 DTO
    
    Returns:
        저장된 SolutionResult 객체
    
    Raises:
        Http404: 해당하는 SpeakerSegment가 없는 경우
    """
    # 1. [Logic] 솔루션 생성기 실행
    generator = SolutionGenerator()
    guide = generator.generate_guide(request_data)

    # 2. [DB] 타겟 세그먼트 조회
    # audio_process 모델에 session_id와 turn_index가 추가되었으므로 바로 검색 가능
    segment = get_object_or_404(
        SpeakerSegment, 
        session_id=request_data.session_id, 
        turn_index=request_data.turn_index
    )

    # 3. [DB] 결과 저장 (Update or Create)
    solution_result, created = SolutionResult.objects.update_or_create(
        segment=segment,
        defaults={
            'input_emotion_label': request_data.emotion_label,
            'input_logical_label': request_data.logical_label,
            'input_logical_type': request_data.logical_type,
            'input_risk_score': request_data.risk_score,
            'input_profanity_category': request_data.profanity_category,
            
            'strategy_title': guide.strategy_title,
            'strategy_description': guide.strategy_description,
            'tone_and_manner': guide.tone_and_manner,
            'required_keywords': guide.required_keywords,
            'prohibited_keywords': guide.prohibited_keywords,
            'solution_scripts': guide.solution_scripts,
            'checkpoints': guide.checkpoints,
            
            'created_at': timezone.now()
        }
    )
    
    return solution_result