from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

# 1. 모델 Import
from audio_process.models import SpeakerSegment
from .models import SolutionResult

# 2. 로직 및 스키마 Import
from .logic.solution_generator import SolutionGenerator
from .schemas import SolutionRequestDTO

@transaction.atomic
def generate_and_save_solution(request_data: SolutionRequestDTO) -> SolutionResult:
    
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