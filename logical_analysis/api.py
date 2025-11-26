from ninja import NinjaAPI, Router
from django.http import JsonResponse
from .schemas import SessionAnalysisRequest
from .services import analyze_and_save_customer_turns

router = Router()

@router.post("/analyze/customer", summary="고객 발화 분석 및 저장")
def analyze_customer_session(request, payload: SessionAnalysisRequest):
    """
    [POST] 세션 STT 데이터를 입력받아 고객 발화만 분석하고 저장합니다.
    (상담원 발화 데이터가 포함되어 있어도 무시하거나 저장하지 않습니다.)
    """
    try:
        result = analyze_and_save_customer_turns(payload)
        return result
        
    except Exception as e:
        # 에러 발생 시 500 응답과 상세 내용 반환
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=500
        )
