from ninja import Router
from django.http import JsonResponse
from .schemas import SolutionRequestDTO, SolutionResponseDTO
from .services import generate_and_save_solution

router = Router()

@router.post("/generate", response=SolutionResponseDTO, summary="상담 솔루션 생성")
def generate_solution_endpoint(request, payload: SolutionRequestDTO):
    """
    [POST] 분석된 발화 데이터(감정, 논리, 리스크 등)를 받아
    적절한 상담 가이드와 스크립트를 생성하여 반환합니다.
    """
    try:
        # 서비스 호출
        result_model = generate_and_save_solution(payload)

        # Response DTO 변환
        return SolutionResponseDTO(
            session_id=payload.session_id,
            turn_index=payload.turn_index,
            
            strategy_title=result_model.strategy_title,
            strategy_description=result_model.strategy_description,
            tone_and_manner=result_model.tone_and_manner,
            
            required_keywords=result_model.required_keywords,
            prohibited_keywords=result_model.prohibited_keywords,
            solution_scripts=result_model.solution_scripts,
            checkpoints=result_model.checkpoints,
            
            created_at=result_model.created_at
        )
    except Exception as e:
        # Router에서는 JsonResponse로 에러 처리
        return JsonResponse(
            {"status": "error", "message": str(e)}, 
            status=500
        )