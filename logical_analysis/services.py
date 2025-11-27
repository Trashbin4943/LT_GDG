from django.db import transaction, models
from django.utils import timezone
from django.db.models import Max
import logging
from typing import Optional

# 1. Pipeline Import
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

# 2. Models Import (SpeakerSegment는 audio_process 앱, Result는 현재 앱)
from audio_process.models import SpeakerSegment, CallRecording
from .models import CustomerAnalysisResult
from .schemas import SessionAnalysisRequest, SegmentInput

# 3. Configuration Import (정적 import로 변경)
from .logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

# 4. Solution System Import (선택적, 런타임에만 사용)
try:
    from solution_system.services import generate_solution_from_analysis
except ImportError:
    generate_solution_from_analysis = None

logger = logging.getLogger(__name__)

# 검증 함수들
def _validate_score(score: float, field_name: str) -> float:
    """점수 범위 검증 및 클리핑 (0.0-1.0)"""
    if score is None:
        return 0.0
    validated = max(0.0, min(1.0, float(score)))
    if validated != score:
        logger.warning(f"{field_name} 점수 범위 조정: {score} → {validated}")
    return validated

def _validate_text(text: str, max_length: int = 10000) -> str:
    """텍스트 검증"""
    if not text:
        return ""
    if len(text) > max_length:
        logger.warning(f"텍스트 길이 초과: {len(text)} > {max_length}, 잘림")
        return text[:max_length]
    return text

def _validate_label(label: str, default: str = "INQUIRY") -> str:
    """라벨 검증"""
    if not label or not label.strip():
        logger.warning(f"라벨이 비어있음, 기본값 사용: {default}")
        return default
    return label.strip()

def _validate_label_type(label: str, label_type: str) -> str:
    """라벨과 라벨 타입 일관성 검증"""
    NORMAL_LABELS = ["INQUIRY", "COMPLAINT", "REQUEST", "CLARIFICATION", "CONFIRMATION", "CLOSING"]
    SPECIAL_LABELS = ["PROFANITY", "VIOLENCE_THREAT", "SEXUAL_HARASSMENT", "HATE_SPEECH", "UNREASONABLE_DEMAND", "REPETITION"]
    
    if label_type == "NORMAL" and label not in NORMAL_LABELS:
        logger.warning(f"라벨 타입 불일치: label={label}, label_type={label_type}, NORMAL로 수정")
        return "NORMAL"
    elif label_type == "SPECIAL" and label not in SPECIAL_LABELS:
        logger.warning(f"라벨 타입 불일치: label={label}, label_type={label_type}, SPECIAL로 수정")
        return "SPECIAL"
    
    return label_type

@transaction.atomic
def analyze_and_save_customer_turns(
    request_data: SessionAnalysisRequest,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    """
    세션 데이터를 받아 파이프라인을 실행하고, '고객(Customer)' 분석 결과만 DB에 저장합니다.
    
    Args:
        request_data: 세션 분석 요청 데이터
        auto_generate_solution: 솔루션 자동 생성 여부 (기본: True)
        skip_existing: 기존 분석 결과가 있으면 스킵 (기본: False)
    
    Returns:
        dict: 분석 결과 통계
    """
    
    # 1. 세션 ID 확인
    session_id = request_data.session_id
    
    # 2. 파이프라인 실행 (고객 발화만 추출하여 텍스트로 변환)
    try:
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        pipeline = MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_enhanced_predictor=True
        )
        
        # 고객 발화만 추출하여 텍스트로 합치기
        customer_texts = []
        segment_map = {}  # turn_index -> segment 정보 매핑
        target_speakers=['customer','client']


        for idx, seg_input in enumerate(request_data.segments):
            if seg_input.speaker in target_speakers:
                if seg_input.text and seg_input.text.strip():
                    customer_texts.append(seg_input.text.strip())
                    segment_map[len(customer_texts) - 1] = {
                        'index': idx,
                        'start_time': seg_input.start_time,
                        'end_time': seg_input.end_time,
                        'text': seg_input.text
                    }
        
        # 고객 발화 텍스트를 합쳐서 파이프라인에 전달
        combined_text = ' '.join(customer_texts) if customer_texts else ''
        if not combined_text:
            logger.warning(f"세션 {session_id}: 고객 발화가 없습니다.")
            return {
                "status": "success",
                "session_id": session_id,
                "processed_customer_turns": 0,
                "skipped_turns": 0,
                "error_turns": 0,
                "generated_solutions": 0
            }
        
        # 파이프라인 실행
        pipeline_result = pipeline.process(combined_text, session_id)
        logger.info(f"파이프라인 실행 완료: session_id={session_id}, results={len(pipeline_result.results)}")
    
    except Exception as e:
        logger.error(f"파이프라인 실행 실패: {e}", exc_info=True)
        raise ValueError(f"파이프라인 실행 실패: {str(e)}")

    # 3. CallRecording 조회
    try:
        recording_obj = CallRecording.objects.get(session_id=str(session_id))
    except CallRecording.DoesNotExist:
        raise ValueError(f"Session ID {str(session_id)} not found in CallRecording.")

    # 4. 결과 순회 및 저장
    saved_count = 0
    skipped_count = 0
    error_count = 0
    solution_count = 0
    
    db_segments = SpeakerSegment.objects.filter(
        session_id=recording_obj,
        speaker_label__in=['customer', 'client']
    )

    segment_lookup = {seg.start_time: seg for seg in db_segments}

    # 파이프라인 결과와 세그먼트를 매핑하여 저장
    for result_idx, classification_result in enumerate(pipeline_result.results):
        
        try:
            origin_info = segment_map.get(result_idx)
            if not origin_info:
                continue
                
            target_start_time = origin_info.get('start_time')

            text = origin_info.get('text','')

            segment = segment_lookup.get(target_start_time)

            if not segment:
                continue
            
            emotion_label = segment.emotion_label or "중립"
            
            if not segment.emotion_label:
                logger.debug(f"Segment {segment.id}: emotion_label 없음, 기본값 '중립' 사용")
            
            # (2) 고객 분석 결과 저장 (검증 포함)
            CustomerAnalysisResult.objects.update_or_create(
                segment=segment,
                defaults={
                    # 분류 결과 (검증 포함)
                    'label': _validate_label(
                        classification_result.label,
                        default="INQUIRY"
                    ),
                    'label_type': _validate_label_type(
                        classification_result.label,
                        classification_result.label_type or "NORMAL"
                    ),
                    'classification_confidence': _validate_score(
                        classification_result.confidence,
                        'classification_confidence'
                    ),
                    'classification_probabilities': classification_result.probabilities or {},
                    
                    # 욕설 감지 결과 (기본값 - 실제로는 profanity_result가 필요)
                    'is_profanity': False,
                    'profanity_category': None,
                    'profanity_method': None,
                    
                    # 주요 리스크 점수 (기본값)
                    'score_risk': getattr(classification_result, 'score_risk', 0.0),
                    'score_profanity': 0.0,
                    'score_threat': 0.0,
                    'score_unreasonable_demand': 0.0,
                    'score_sexual_harassment': 0.0,
                    'score_hate_speech': 0.0,
                    'score_repetition': 0.0,
                    
                    # 상세 정보
                    'feature_scores_extra': {},
                    'extracted_features': {},
                    
                    'analyzed_at': timezone.now()
                }
            )

            if segment.text != text:
                segment.text = text
                segment.save(update_fields=['text'])
            
            # 3. solution_system 자동 호출
            if auto_generate_solution and generate_solution_from_analysis:
                try:
                    generate_solution_from_analysis(segment, emotion_label)
                    solution_count += 1
                    logger.debug(f"Segment {segment.id} 솔루션 생성 완료")
                except Exception as e:
                    logger.warning(
                        f"Segment {segment.id} 솔루션 생성 실패 (분석 결과는 저장됨): {e}",
                        exc_info=True
                    )
            elif auto_generate_solution and not generate_solution_from_analysis:
                logger.warning(f"Segment {segment.id}: solution_system을 사용할 수 없습니다.")
            
            saved_count += 1
            logger.debug(f"Segment {segment.id} 분석 결과 저장 완료: label={classification_result.label}")
            
        except Exception as e:
            error_count += 1
            logger.error(
                f"Result {result_idx} 분석 결과 저장 실패: {e}",
                exc_info=True
            )
            continue
            
    logger.info(
        f"세션 {session_id} 분석 완료: "
        f"저장={saved_count}, 스킵={skipped_count}, 에러={error_count}, 솔루션={solution_count}"
    )
            
    return {
        "status": "success",
        "session_id": str(session_id),
        "processed_customer_turns": saved_count,
        "skipped_turns": skipped_count,
        "error_turns": error_count,
        "generated_solutions": solution_count if auto_generate_solution else 0
    }


def _convert_segments_to_request(recording: CallRecording) -> SessionAnalysisRequest:
    """
    DB의 SpeakerSegment를 SessionAnalysisRequest로 변환합니다.
    STT 데이터 양식을 통일하여 처리합니다.
    
    Args:
        recording: CallRecording 객체
        
    Returns:
        SessionAnalysisRequest 객체
    """
    segments = recording.segments.all().order_by('turn_index', 'start_time')
    
    segment_inputs = []
    for seg in segments:
        # speaker_label을 통일된 형식으로 변환 (client -> customer, counselor -> agent)
        speaker = seg.speaker_label
        if speaker == 'client':
            speaker = 'customer'
        elif speaker == 'counselor':
            speaker = 'agent'
        elif speaker == 'unknown':
            # unknown은 is_counselor 필드로 판단
            speaker = 'agent' if seg.is_counselor else 'customer'
        
        segment_inputs.append(SegmentInput(
            speaker=speaker,
            text=seg.text or "",
            start_time=float(seg.start_time) if seg.start_time else None,
            end_time=float(seg.end_time) if seg.end_time else None,
            timestamp=None  # 필요시 추가
        ))
    
    return SessionAnalysisRequest(
        session_id=str(recording.session_id),
        segments=segment_inputs
    )


@transaction.atomic
def analyze_from_db_segments(
    recording: CallRecording,
    auto_generate_solution: bool = True,
    skip_existing: bool = False
):
    """
    DB의 SpeakerSegment에서 직접 데이터를 읽어 분석합니다.
    emotion_system과 동일한 방식으로 데이터를 처리합니다.
    
    Args:
        recording: CallRecording 객체
        auto_generate_solution: 솔루션 자동 생성 여부
        skip_existing: 기존 분석 결과 스킵 여부
        
    Returns:
        dict: 분석 결과 통계
    """
    # 1. DB에서 데이터를 SessionAnalysisRequest 형식으로 변환
    request_data = _convert_segments_to_request(recording)
    
    # 2. 기존 함수 재사용
    return analyze_and_save_customer_turns(
        request_data,
        auto_generate_solution=auto_generate_solution,
        skip_existing=skip_existing
    )