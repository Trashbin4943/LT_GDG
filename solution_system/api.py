from ninja import Router
from accounts.jwt_auth import JWTAuth
from .schemas import SolutionRequestDTO, SolutionResponseDTO
from .services import generate_and_save_solution

router = Router()

@router.post("/generate", response=SolutionResponseDTO, summary="상담 솔루션 생성", auth=JWTAuth())
def generate_solution_endpoint(request, payload: SolutionRequestDTO):
    """
    [POST] 분석된 발화 데이터(감정, 논리, 리스크 등)를 받아
    적절한 상담 가이드와 스크립트를 생성하여 반환합니다.
    
    요구 사항:
    - session_id: 통화 세션 ID
    - turn_index: 발화 순서
    - text: 고객 발화 텍스트
    - emotion_label: 감정 분류 결과
    - logical_label: 논리 분류 결과
    - logical_type: 논리 타입 (NORMAL/SPECIAL)
    - risk_score: 위험도 점수 (0.0~1.0)
    - profanity_category: 욕설 카테고리
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
        # Ninja 라우터: dict 응답으로 에러 처리
        return {
            "status": "error",
            "message": f"솔루션 생성 중 오류 발생: {str(e)}",
            "session_id": payload.session_id,
            "turn_index": payload.turn_index
        }