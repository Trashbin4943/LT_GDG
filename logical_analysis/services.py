import logging
import uuid
from typing import List, Optional
from django.db import transaction
from django.utils import timezone

# 1. Pipeline Import
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

# 2. Models & Schemas Import
from audio_process.models import SpeakerSegment, CallRecording
from .models import CustomerAnalysisResult
from .schemas import SessionAnalysisRequest, SegmentInput

# 3. Configuration Import
from .logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

# 4. Solution System Import (선택적)
try:
    from solution_system.services import generate_solution_from_analysis
except ImportError:
    generate_solution_from_analysis = None

logger = logging.getLogger(__name__)

# 분석 결과에서 상세 점수를 안전하게 가져오는 헬퍼 함수
def _safe_get_score(ai_result: object, score_name: str) -> float:
    """ai_result 객체에서 특정 점수를 안전하게 가져옴. 없으면 0.0 반환"""
    return getattr(ai_result, score_name, 0.0)

@transaction.atomic
def analyze_and_save_customer_turns(
    request_data: SessionAnalysisRequest,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    session_id = request_data.session_id
    print(f"[분석 시작] Session: {session_id}")

    # 1. 기존 분석 데이터 초기화
    try:
        recording_obj = CallRecording.objects.get(session_id=str(session_id))
        segment_ids = SpeakerSegment.objects.filter(session_id=recording_obj).values_list('id', flat=True)
        deleted, _ = CustomerAnalysisResult.objects.filter(segment_id__in=segment_ids).delete()
        print(f"초기화: 기존 결과 {deleted}건 삭제 완료")
    except Exception as e:
        print(f"경고: 초기화 중 오류 발생 - {e}")
        pass

    # 2. 파이프라인 초기화
    try:
        pipeline = MainPipeline(
            intensity_model_path=get_intensity_model_path(),
            ternary_model_path=get_ternary_model_path(),
            use_enhanced_predictor=True,
            use_two_stage_session=False
        )
    except Exception as e:
        raise ValueError(f"AI 모델 로딩 실패: {str(e)}")

    # 3. DB 세그먼트 로드 및 매핑 준비
    db_segments = SpeakerSegment.objects.filter(session_id=recording_obj)
    db_segment_lookup = {seg.id: seg for seg in db_segments}
    
    saved_count = 0
    target_speakers = ['customer', 'client']

    # 4. 분석 루프
    for idx, seg_input in enumerate(request_data.segments):

        if seg_input.speaker.lower() not in target_speakers:
            continue
        input_text = seg_input.text.strip()
        if not input_text:
            continue

        segment_id = getattr(seg_input, 'id', None) 
        if segment_id is None:
            print(f"경고: Index {idx}의 SegmentInput에 ID 필드가 누락되었습니다. 스킵합니다.")
            continue
            
        segment = db_segment_lookup.get(segment_id)
        if not segment:
            continue
            
        db_text_clean = segment.text.strip().replace(" ", "")
        input_text_clean = input_text.replace(" ", "")
        
        if db_text_clean[:10] != input_text_clean[:10]:
            print(f"[데이터 불일치] ID:{segment_id} 스킵 (DB: {segment.text[:10]}... vs Input: {input_text[:10]}...)")
            continue

        try:
            fake_session_id = str(uuid.uuid4())

            ai_result = pipeline.process_single_sentence(segment.text, fake_session_id)
            
            final_risk_score = _safe_get_score(ai_result, 'score_risk')

            CustomerAnalysisResult.objects.create(
                segment=segment,
                label=ai_result.label,
                label_type=ai_result.label_type,
                classification_confidence=ai_result.confidence,
                classification_probabilities=ai_result.probabilities or {},
                
                score_risk=final_risk_score,
                score_profanity=_safe_get_score(ai_result, 'score_profanity'),
                score_threat=_safe_get_score(ai_result, 'score_threat'),
                score_unreasonable_demand=_safe_get_score(ai_result, 'score_unreasonable_demand'),
                score_sexual_harassment=_safe_get_score(ai_result, 'score_sexual_harassment'),
                score_hate_speech=_safe_get_score(ai_result, 'score_hate_speech'),
                score_repetition=_safe_get_score(ai_result, 'score_repetition'),

                is_profanity=True if final_risk_score >= 0.7 or ai_result.label == 'PROFANITY' else False,
                analyzed_at=timezone.now()
            )
            
            if auto_generate_solution and generate_solution_from_analysis:
                try:
                    emotion = segment.emotion_label or "중립"
                    generate_solution_from_analysis(segment, emotion)
                except Exception:
                    pass

            saved_count += 1
            
            if hasattr(pipeline, 'session_manager'):
                 pipeline.session_manager.clear_session(fake_session_id)


        except Exception as e:
            print(f"분석 중 에러 (ID {segment_id}): {e}")
            continue

    print(f"최종 저장 완료: {saved_count}건")
    
    return {
        "status": "success",
        "processed_customer_turns": saved_count,
        "generated_solutions": 0
    }


def _convert_segments_to_request(recording: CallRecording) -> SessionAnalysisRequest:
    segments = recording.segments.all().order_by('turn_index', 'start_time', 'id')
    segment_inputs = []
    for seg in segments:
        speaker = seg.speaker_label
        if speaker == 'client': speaker = 'customer'
        elif speaker == 'counselor': speaker = 'agent'
        elif speaker == 'unknown': speaker = 'agent' if getattr(seg, 'is_counselor', False) else 'customer'
        
        start_t = getattr(seg, 'start_time', 0.0)
        end_t = getattr(seg, 'end_time', 0.0)

        segment_inputs.append(SegmentInput(
            id=seg.id,
            speaker=speaker,
            text=seg.text or "",
            start_time=float(start_t),
            end_time=float(end_t),
            timestamp=None 
        ))
    return SessionAnalysisRequest(session_id=str(recording.session_id), segments=segment_inputs)

@transaction.atomic
def analyze_from_db_segments(recording: CallRecording, auto_generate_solution: bool = True, skip_existing: bool = False):
    request_data = _convert_segments_to_request(recording)
    return analyze_and_save_customer_turns(request_data, auto_generate_solution=auto_generate_solution, skip_existing=skip_existing)