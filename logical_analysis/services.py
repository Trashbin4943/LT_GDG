from django.db import transaction
from django.utils import timezone
import logging

# 1. Pipeline Import
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

# 2. Models Import (SpeakerSegment는 audio_process 앱, Result는 현재 앱)
from audio_process.models import SpeakerSegment, CallRecording
from .models import CustomerAnalysisResult
from .schemas import SessionAnalysisRequest

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
    
    # 1. 파이프라인 실행 (모델 경로 전달)
    try:
        from .logic_classify_system.config.model_paths import get_intensity_model_path, get_ternary_model_path
        
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        pipeline = MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_enhanced_predictor=True
        )
        pipeline_result = pipeline.process(request_data.model_dump())
        logger.info(f"파이프라인 실행 완료: session_id={pipeline_result.session_id}, turns={len(pipeline_result.turn_results)}")
    except Exception as e:
        logger.error(f"파이프라인 실행 실패: {e}", exc_info=True)
        raise ValueError(f"파이프라인 실행 실패: {str(e)}")
    
    session_id = pipeline_result.session_id
    saved_count = 0
    skipped_count = 0
    error_count = 0
    solution_count = 0

    try:
        recording_obj = CallRecording.objects.get(session_id=str(session_id))
    except CallRecording.DoesNotExist:
        raise ValueError(f"Session ID {str(session_id)} not found in CallRecording.")

    # 2. 결과 순회 및 저장
    for turn_res in pipeline_result.turn_results:
        
        # Customer Result가 존재하는 경우만 처리 (Agent 무시)
        if not turn_res.customer_result:
            continue
        
        try:
            c_res = turn_res.customer_result
            turn_index = turn_res.turn_index
            timestamp = timezone.now()

            # (1) 부모 세그먼트 저장/조회 (audio_process 앱)
            segment, created = SpeakerSegment.objects.get_or_create(
                session_id=recording_obj,
                turn_index=turn_index,
                defaults={
                    'text': _validate_text(c_res.text),
                    'speaker_label': 'customer',
                    'start_time': 0.0,
                    'end_time': 0.0
                }
            )
            
            # [NEW] 기존 분석 결과 스킵 옵션
            if skip_existing and hasattr(segment, 'customer_analysis'):
                skipped_count += 1
                logger.debug(f"Turn {turn_index} 분석 결과 스킵 (이미 존재)")
                continue
            
            # [NEW] emotion_label 확인 (emotion_system에서 가져옴)
            emotion_label = segment.emotion_label or "중립"
            if not segment.emotion_label:
                logger.warning(f"Turn {turn_index}: emotion_label이 없음, 기본값 '중립' 사용")

            # (2) 고객 분석 결과 저장 (검증 포함)
            CustomerAnalysisResult.objects.update_or_create(
                segment=segment,
                defaults={
                    # 분류 결과 (검증 포함)
                    'label': _validate_label(
                        c_res.classification_result.label,
                        default="INQUIRY"
                    ),
                    'label_type': _validate_label_type(
                        c_res.classification_result.label,
                        c_res.classification_result.label_type or "NORMAL"
                    ),
                    'classification_confidence': _validate_score(
                        c_res.classification_result.confidence,
                        'classification_confidence'
                    ),
                    'classification_probabilities': c_res.classification_result.probabilities or {},

                    # 욕설 감지 결과 (검증 포함)
                    'is_profanity': bool(c_res.profanity_result.is_profanity),
                    'profanity_category': c_res.profanity_result.category or None,
                    'profanity_method': c_res.profanity_result.method or None,  # [FIX] 추가!
                    
                    # 주요 리스크 점수 (검증 포함)
                    'score_risk': _validate_score(
                        turn_res.turn_scores.get('turn_risk_score', 0.0),
                        'score_risk'
                    ),
                    'score_profanity': _validate_score(
                        c_res.feature_scores.get('profanity_score', 0.0),
                        'score_profanity'
                    ),
                    'score_threat': _validate_score(
                        c_res.feature_scores.get('threat_score', 0.0),
                        'score_threat'
                    ),
                    'score_unreasonable_demand': _validate_score(
                        c_res.feature_scores.get('unreasonable_demand_score', 0.0),
                        'score_unreasonable_demand'
                    ),
                    'score_sexual_harassment': _validate_score(
                        c_res.feature_scores.get('sexual_harassment_score', 0.0),
                        'score_sexual_harassment'
                    ),
                    'score_hate_speech': _validate_score(
                        c_res.feature_scores.get('hate_speech_score', 0.0),
                        'score_hate_speech'
                    ),
                    'score_repetition': _validate_score(
                        c_res.feature_scores.get('repetition_keyword_score', 0.0),
                        'score_repetition'
                    ),

                    # 상세 정보 (JSON Fields)
                    'feature_scores_extra': c_res.feature_scores or {},
                    'extracted_features': c_res.extracted_features or {},
                    
                    'analyzed_at': timestamp
                }
            )
            
            # [NEW] 3. solution_system 자동 호출
            if auto_generate_solution:
                try:
                    from solution_system.services import generate_solution_from_analysis
                    generate_solution_from_analysis(segment, emotion_label)
                    solution_count += 1
                    logger.debug(f"Turn {turn_index} 솔루션 생성 완료")
                except Exception as e:
                    # 솔루션 생성 실패해도 분석 결과는 저장
                    logger.warning(
                        f"Turn {turn_index} 솔루션 생성 실패 (분석 결과는 저장됨): {e}",
                        exc_info=True
                    )
            
            saved_count += 1
            logger.debug(f"Turn {turn_index} 분석 결과 저장 완료: label={c_res.classification_result.label}, risk={turn_res.turn_scores.get('turn_risk_score', 0.0)}")
            
        except Exception as e:
            error_count += 1
            logger.error(
                f"Turn {turn_index} 분석 결과 저장 실패: {e}",
                exc_info=True
            )
            # 개별 Turn 실패해도 계속 진행
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