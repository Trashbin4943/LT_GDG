# logical_analysis/api.py

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count
from datetime import datetime
from accounts.jwt_auth import JWTAuth

from audio_process.models import CallRecording, SpeakerSegment
from .models import CustomerAnalysisResult
from .schemas import CustomerAnalysisResponseSchema, SessionAnalysisRequest
from .services import analyze_and_save_customer_turns, analyze_from_db_segments

router = Router()


@router.post("/analyze/customer", summary="고객 발화 분석 및 저장", auth=JWTAuth())
def analyze_customer_session(
    request, 
    payload = None,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    """
    [POST] 세션 STT 데이터를 입력받아 고객 발화만 분석하고 저장합니다.
    """
    try:
        result = analyze_and_save_customer_turns(
            payload,
            auto_generate_solution=auto_generate_solution,
            skip_existing=skip_existing
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/analyze/customer/{session_id}", summary="DB에서 고객 발화 분석 및 저장", auth=JWTAuth())
def analyze_customer_session_from_db(
    request,
    session_id: str,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    """
    [POST] session_id를 받아서 DB의 SpeakerSegment에서 직접 데이터를 읽어 분석합니다.
    """
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    try:
        result = analyze_from_db_segments(
            recording,
            auto_generate_solution=auto_generate_solution,
            skip_existing=skip_existing
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/{session_id}", response=CustomerAnalysisResponseSchema)
def get_analysis_result(request, session_id: str):
    """세션별 논리 분석 결과 조회"""
    recording = get_object_or_404(CallRecording, session_id=session_id)
    segments = recording.segments.select_related('customer_analysis').all().order_by('start_time')
    
    output_results = []
    valid_results = []
    
    for seg in segments:
        if hasattr(seg, 'customer_analysis'):
            res = seg.customer_analysis
            valid_results.append(res)
            
            output_results.append({
                "text": seg.text,
                "label": res.label,
                "label_type": res.label_type,
                "classification_confidence": res.classification_confidence,
                "probabilities": res.classification_probabilities,

                "score_risk":res.score_risk,
                "is_profanity": res.is_profanity,

                "timestamp": res.timestamp,
                "created_at": res.created_at
            })

    total_count = len(valid_results)
    risk_count = sum(1 for r in valid_results 
                     if r.label_type=='SPECIAL' or r.score_risk >= 0.6)
    
    highest = 'LOW'
    if any(r.score_risk >= 0.8 for r in valid_results):
        highest = 'CRITICAL'
    elif any(r.score_risk >= 0.6 for r in valid_results):
        highest = 'HIGH'
    elif any(r.label_type == 'SPECIAL' for r in valid_results):
        highest = 'MEDIUM'

    most_common_label = "None"
    if total_count > 0:
        from collections import Counter
        counts = Counter([r.label for r in valid_results])
        most_common_label = counts.most_common(1)[0][0]

    summary_data = {
        "total_sentences": total_count,
        "risk_count": risk_count,
        "highest_risk_score": highest,
        "primary_label": most_common_label
    }

    return {
        "session_id": str(recording.session_id),
        "created_at": recording.created_at,
        "summary": summary_data,
        "results": output_results
    }