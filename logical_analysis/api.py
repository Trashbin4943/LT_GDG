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
    # customer_analysis를 select_related로 프리페치
    segments = recording.segments.select_related('customer_analysis').all().order_by('start_time')
    
    output_results = []
    valid_results = []
    total_risk_score = 0.0 # 평균 리스크 계산용
    
    for seg in segments:
        if hasattr(seg, 'customer_analysis'):
            res = seg.customer_analysis
            valid_results.append(res)
            total_risk_score += res.score_risk # 리스크 점수 합산
            
            # 1. 상세 점수 (FeatureScores) 객체 생성
            feature_scores_data = {
                "profanity_score": res.score_profanity,
                "threat_score": res.score_threat,
                "unreasonable_demand_score": res.score_unreasonable_demand,
                "sexual_harassment_score": res.score_sexual_harassment,
                "hate_speech_score": res.score_hate_speech,
                "repetition_keyword_score": res.score_repetition,
            }
            
            output_results.append({
                "text": seg.text,
                "label": res.label,
                "label_type": res.label_type,
                "classification_confidence": res.classification_confidence,
                "probabilities": res.classification_probabilities,
                "score_risk":res.score_risk,
                "is_profanity": res.is_profanity,
                "profanity_category": res.profanity_category, 
                "profanity_method": res.profanity_method, 
                
                "feature_scores": feature_scores_data, 
                "extracted_features": res.extracted_features, 
                
                "timestamp": seg.start_time, # seg에서 가져옴 (시간 정보)
                "created_at": res.analyzed_at # res에서 가져옴 (분석 시각)
            })

    total_count = len(valid_results)
    avg_risk_score = (total_risk_score / total_count) if total_count > 0 else 0.0
    
    # 리스크 레벨 계산 로직은 유지
    highest_alert = 'LOW'
    if any(r.score_risk >= 0.8 for r in valid_results):
        highest_alert = 'CRITICAL'
    elif any(r.score_risk >= 0.6 for r in valid_results):
        highest_alert = 'HIGH'
    elif any(r.label_type == 'SPECIAL' for r in valid_results):
        highest_alert = 'MEDIUM'

    most_common_label = "None"
    if total_count > 0:
        from collections import Counter
        counts = Counter([r.label for r in valid_results])
        most_common_label = counts.most_common(1)[0][0]

    summary_data = {
        "total_sentences": total_count,
        "risk_score": round(avg_risk_score, 4), 
        "highest_alert": highest_alert, 
        "primary_intent": most_common_label 
    }

    return {
        "session_id": str(recording.session_id),
        "created_at": recording.created_at,
        "summary": summary_data,
        "results": output_results
    }