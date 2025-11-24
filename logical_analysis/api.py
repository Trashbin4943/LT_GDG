# logical_analysis/api.py

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count
from datetime import datetime

from audio_process.models import CallRecording, SpeakerSegment
from .models import LogicalResult as ClassificationResult
from .schemas import AnalyzeRequest, AnalysisSessionOut, ClassificationResultOut
from .inference import run_pipeline

router = Router()

@router.post("/analyze")
def run_analysis_for_session(request, payload: AnalyzeRequest):
    recording = get_object_or_404(CallRecording, session_id=payload.session_id)
    segments = recording.segments.all()
    
    if not segments.exists():
        return {"status": "error", "message": "분석할 텍스트 데이터(Segments)가 없습니다."}

    saved_count = 0
    
    with transaction.atomic():
        results_to_create = []
        
        for seg in segments:
            if hasattr(seg, 'logical_analysis'):
                continue

            ai_res = run_pipeline(seg.text, payload.session_id) 
            res_data = ai_res.results[0] if hasattr(ai_res, 'results') and ai_res.results else ai_res

            results_to_create.append(ClassificationResult(
                segment=seg,
                label=res_data.label,
                label_type=res_data.label_type,
                confidence=res_data.confidence,
                probabilities=res_data.probabilities or {},
                action=getattr(res_data, 'action', 'MONITOR'),
                alert_level=getattr(res_data, 'alert_level', 'LOW'),
                timestamp=datetime.now()
            ))

        if results_to_create:
            ClassificationResult.objects.bulk_create(results_to_create)
            saved_count = len(results_to_create)
            

    return {
        "status": "success",
        "session_id": payload.session_id,
        "analyzed_segments": saved_count
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