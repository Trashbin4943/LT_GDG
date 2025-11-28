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
            use_two_stage_session=True
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


            # [Process Single Sentence 로직]
            # ai_result = pipeline.process_single_sentence(segment.text, fake_session_id)
            

            # intensity_val = ai_result.intensity if ai_result.intensity is not None else 0.0
            # is_immoral_val = ai_result.is_immoral if ai_result.is_immoral is not None else False
            # prob_val = ai_result.probabilities if ai_result.probabilities else {}

            # if not ai_result.intensity or not ai_result.is_immoral or not ai_result.probabilities:
            #     print("AI 논리분석 결과 추출 오류 발생: services.py.analysze_and_save_customer_returns")
            #     print(f"ai_result.intensity= {ai_result.intensity}")
            #     print(f"ai_result.is_immoral= {ai_result.is_immoral}")
            #     print(f"ai_result.probabilities= {ai_result.probabilities}")

            # final_is_profanity = (
            #     score_risk >= 0.7 or
            #     ai_result.label == 'PROFANITY' or
            #     (is_immoral_val and ai_result.intensity_level == "HIGH")
            # )

            ai_result = pipeline.process_single_sentence_two_stage(segment.text, fake_session_id)
            print(f"DEBUG Check - Text: {segment.text[:10]}... | Intensity: {getattr(ai_result, 'intensity', 'None')} | Immoral: {getattr(ai_result, 'is_immoral', 'None')}")
            scores = getattr(ai_result, 'final_scores', {})

            extended_probs = ai_result.probabilities or {}
            extended_probs.update({
                "metadata_intensity": getattr(ai_result, 'intensity', 0.0),
                "metadata_intensity_level": getattr(ai_result, 'intensity_level', 'LOW'),
                "metadata_is_immoral": getattr(ai_result, 'is_immoral', False),
                "metadata_immorality_confidence": getattr(ai_result, 'immorality_confidence', 0.0)
            })

            final_risk_score = calculate_dynamic_risk_score(ai_result)

            print(f"리스크 점수: {scores}")

            CustomerAnalysisResult.objects.create(
                segment=segment,

                label=ai_result.label,
                label_type=ai_result.label_type,
                classification_confidence=ai_result.confidence,
                # classification_probabilities=prob_val,
                classification_probabilities=extended_probs,

                intensity=getattr(ai_result, 'intensity', 0.0),
                intensity_level=getattr(ai_result, 'intensity_level', 'LOW'),
                is_immoral=getattr(ai_result, 'is_immoral', False),
                immorality_confidence=getattr(ai_result, 'immorality_confidence', 0.0),
                
                score_risk = final_risk_score,
                score_profanity=getattr(ai_result, 'score_profanity', 0.0),
                score_threat=getattr(ai_result, 'score_threat', 0.0),
                score_unreasonable_demand=scores.get('unreasonable_demand_score', 0.0),
                score_sexual_harassment=scores.get('sexual_harassment_score', 0.0),
                score_hate_speech=scores.get('hate_speech_score', 0.0),
                score_repetition=scores.get('repetition_score', 0.0),

                is_profanity=(scores.get('risk_score', 0.0) >= 0.3),

                
                # is_profanity = final_is_profanity,


                # intensity = intensity_val,
                # intensity_level = ai_result.intensity_level,
                # is_immoral = is_immoral_val,
                # immorality_confidence=ai_result.immorality_confidence,

                # score_risk=final_risk_score,
                # score_profanity=_safe_get_score(ai_result, 'score_profanity'),
                # score_threat=_safe_get_score(ai_result, 'score_threat'),
                # score_unreasonable_demand=_safe_get_score(ai_result, 'score_unreasonable_demand'),
                # score_sexual_harassment=_safe_get_score(ai_result, 'score_sexual_harassment'),
                # score_hate_speech=_safe_get_score(ai_result, 'score_hate_speech'),
                # score_repetition=_safe_get_score(ai_result, 'score_repetition'),

                
                analyzed_at=timezone.now()
            )
            
            # if auto_generate_solution and generate_solution_from_analysis:
            #     try:
            #         emotion = segment.emotion_label or "중립"
            #         generate_solution_from_analysis(segment, emotion)
            #     except Exception:
            #         pass

            # saved_count += 1
            
            # if hasattr(pipeline, 'session_manager'):
            #      pipeline.session_manager.clear_session(fake_session_id)

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

def calculate_dynamic_risk_score(ai_result):
    # 1. Label별 기본 위험도 (Base Score)
    base_score_map = {
        'THREAT': 0.9,            # 위협
        'SEXUAL_HARASSMENT': 0.9, # 성희롱
        'HATE_SPEECH': 0.8,       # 혐오 발언
        'PROFANITY': 0.7,         # 욕설
        'UNREASONABLE_DEMAND': 0.5, # 무리한 요구
        'COMPLAINT': 0.3,         # 불만
        'NORMAL': 0.0             # 일반
    }
    base_score = base_score_map.get(ai_result.label, 0.0)

    intensity_val = ai_result.intensity if ai_result.intensity else 0.0
    intensity_boost = min(intensity_val * 0.1, 0.3)

    immorality_boost = 0.15 if ai_result.is_immoral else 0.0

    total_risk = base_score + intensity_boost + immorality_boost

    return min(round(total_risk, 4), 1.0)