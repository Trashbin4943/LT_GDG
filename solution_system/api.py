# logical_analysis/api.py (또는 관련 view 파일)

from ninja import Router
from solution_system.schemas import SolutionRequestDTO, SolutionResponseDTO
from solution_system.logic.solution_generator import SolutionGenerator
from accounts.jwt_auth import JWTAuth

from .models import SolutionResult
from audio_process.models import SpeakerSegment
from django.utils import timezone

router = Router(tags=["Solution"])

@router.post("/generate", response=SolutionResponseDTO, auth=JWTAuth())
def generate_solution_api(request, payload: SolutionRequestDTO):
    
    try:
        generator = SolutionGenerator()
        guide = generator.generate_guide(payload)
        
        segment_obj = SpeakerSegment.objects.get(id=payload.segment_id)
        guide_result = generator.generate_guide(payload)
        
        SolutionResult.objects.update_or_create(
            segment=segment_obj,
            defaults={
                "strategy_title": guide.strategy_title,
                "strategy_description": guide.strategy_description,
                "tone_and_manner": guide.tone_and_manner,
                "solution_scripts": guide.solution_scripts,
                "checkpoints": guide.checkpoints,
                "updated_at": timezone.now()
            }
        )

        return SolutionResponseDTO(
            strategy_title=guide_result.strategy_title,
            strategy_description=guide_result.strategy_description,
            tone_and_manner=guide_result.tone_and_manner,
            solution_scripts=guide_result.solution_scripts,
            checkpoints=guide_result.checkpoints
        )
        
    except Exception as e:
        print(f"[Solution Gen Error] {str(e)}")
        raise e