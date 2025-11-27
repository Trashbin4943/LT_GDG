# logical_analysis/api.py

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count
from datetime import datetime
from ninja_jwt.authentication import JWTAuth

from audio_process.models import CallRecording, SpeakerSegment
from .models import ClassificationResult
from .schemas import AnalyzeRequest, AnalysisSessionOut, ClassificationResultOut, SessionAnalysisRequest
from .services import analyze_and_save_customer_turns, analyze_from_db_segments

router = Router()


@router.post("/analyze/customer", summary="고객 발화 분석 및 저장", auth=JWTAuth())
def analyze_customer_session(
    request, 
    payload: SessionAnalysisRequest,
    auto_generate_solution: bool = True,  # 자동 솔루션 생성 여부
    skip_existing: bool = False  # 기존 분석 결과 스킵 여부
):
    """
    [POST] 세션 STT 데이터를 입력받아 고객 발화만 분석하고 저장합니다.
    (상담원 발화 데이터가 포함되어 있어도 무시하거나 저장하지 않습니다.)
    
    Args:
        auto_generate_solution: 분석 완료 후 솔루션 자동 생성 여부 (기본: True)
        skip_existing: 기존 분석 결과가 있으면 스킵 여부 (기본: False)
    """
    try:
        result = analyze_and_save_customer_turns(
            payload,
            auto_generate_solution=auto_generate_solution,
            skip_existing=skip_existing
        )
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/analyze/customer/{session_id}", summary="DB에서 고객 발화 분석 및 저장", auth=JWTAuth())
def analyze_customer_session_from_db(
    request,
    session_id: str,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    """
    [POST] session_id를 받아서 DB의 SpeakerSegment에서 직접 데이터를 읽어 분석합니다.
    emotion_system과 통일된 방식으로 데이터를 처리합니다.
    
    Args:
        session_id: 세션 ID
        auto_generate_solution: 솔루션 자동 생성 여부
        skip_existing: 기존 분석 결과 스킵 여부
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
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/{session_id}", response=AnalysisSessionOut)
def get_analysis_result(request, session_id: str):

    recording = get_object_or_404(CallRecording, session_id=session_id)
    segments = recording.segments.select_related('logical_analysis').all().order_by('start_time')
    
    output_results = []
    valid_results = []
    
    for seg in segments:
        if hasattr(seg, 'logical_analysis'):
            res = seg.logical_analysis
            valid_results.append(res)
            
            output_results.append({
                "text": seg.text,
                "label": res.label,
                "label_type": res.label_type,
                "confidence": res.confidence,
                "probabilities": res.probabilities,
                "action": res.action,
                "alert_level": res.alert_level,
                "timestamp": res.timestamp,
                "created_at": res.created_at
            })

    total_count = len(valid_results)
    risk_count = sum(1 for r in valid_results if r.alert_level in ['HIGH', 'CRITICAL'])
    
    alert_levels = {r.alert_level for r in valid_results}
    if 'CRITICAL' in alert_levels: highest = 'CRITICAL'
    elif 'HIGH' in alert_levels: highest = 'HIGH'
    elif 'MEDIUM' in alert_levels: highest = 'MEDIUM'
    else: highest = 'LOW'

    most_common_label = "None"
    if total_count > 0:
        from collections import Counter
        counts = Counter([r.label for r in valid_results])
        most_common_label = counts.most_common(1)[0][0]

    summary_data = {
        "total_sentences": total_count,
        "risk_score": risk_count,
        "highest_alert": highest,
        "primary_intent": most_common_label
    }

    return {
        "session_id": recording.session_id,
        "created_at": recording.created_at,
        "summary": summary_data,
        "results": output_results
    }