from django.db import transaction, models
from django.utils import timezone
from django.db.models import Max
import logging
from typing import Optional

# 1. Pipeline Import
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

# 2. Feature Extractor Import (baseline 점수 계산용)
try:
    from .logic_classify_system.feature_extractor.customer_feature_extractor import CustomerFeatureExtractor
    from .logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
except ImportError:
    CustomerFeatureExtractor = None
    ProfanityDetector = None

# 3. Models Import (SpeakerSegment는 audio_process 앱, Result는 현재 앱)
from audio_process.models import SpeakerSegment, CallRecording
from .models import CustomerAnalysisResult
from .schemas import SessionAnalysisRequest, SegmentInput

# 4. Configuration Import (정적 import로 변경)
from .logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

# 5. Solution System Import (선택적, 런타임에만 사용)
try:
    from solution_system.services import generate_solution_from_analysis
except ImportError:
    generate_solution_from_analysis = None

logger = logging.getLogger(__name__)

# 검증 함수들은 session_utils로 이동됨 (하위 호환성을 위해 import)
from .logic_classify_system.pipeline.session_utils import (
    validate_score as _validate_score,
    validate_text as _validate_text,
    validate_label as _validate_label,
    validate_label_type as _validate_label_type
)

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
        # 모델 경로 가져오기
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        # AI hub 모델 경로 설정 (환경 변수 또는 기본 경로)
        import os
        from pathlib import Path
        from .logic_classify_system.models import AIHUB_MODEL_DIR
        
        # AI hub 모델 경로
        aihub_base_path = os.getenv('AIHUB_BASE_MODEL_PATH') or str(AIHUB_MODEL_DIR)
        aihub_model1_checkpoint = os.getenv('AIHUB_MODEL1_CHECKPOINT')
        aihub_model2_checkpoint = os.getenv('AIHUB_MODEL2_CHECKPOINT')
        
        # AI Hub 모델 경로 로깅 (서버 로그 확인용)
        logger.info(f"AI Hub 모델 경로 설정 - session_id: {session_id}")
        logger.info(f"  base_path: {aihub_base_path}")
        logger.info(f"  base_path 존재 여부: {Path(aihub_base_path).exists() if aihub_base_path else False}")
        logger.info(f"  model1_checkpoint: {aihub_model1_checkpoint}")
        logger.info(f"  model2_checkpoint: {aihub_model2_checkpoint}")
        
        # 두 단계 세션 구조로 파이프라인 초기화
        pipeline = MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_two_stage_session=True,  # 새로운 두 단계 세션 구조 사용
            aihub_base_path=aihub_base_path if Path(aihub_base_path).exists() else None,
            aihub_model1_checkpoint=aihub_model1_checkpoint,
            aihub_model2_checkpoint=aihub_model2_checkpoint
        )
        
        # AI Hub 모델 로드 상태 확인 및 로깅
        if hasattr(pipeline, 'baseline_session') and pipeline.baseline_session:
            aihub_status = pipeline.baseline_session.get_session_info().get('has_aihub_model', False)
            if aihub_status:
                logger.info(f"✅ AI Hub 모델 로드 성공 - session_id: {session_id}")
            else:
                logger.warning(f"❌ AI Hub 모델 로드 실패 (Baseline 규칙만 사용) - session_id: {session_id}")
        else:
            logger.warning(f"⚠️ BaselineSession이 초기화되지 않음 - session_id: {session_id}")
        
        # 고객 발화만 추출하여 개별 세그먼트 단위로 처리
        customer_segments = []
        segment_map = {}  # pipeline_result_idx -> segment 정보 매핑
        target_speakers=['customer','client']

        for idx, seg_input in enumerate(request_data.segments):
            if seg_input.speaker in target_speakers:
                if seg_input.text and seg_input.text.strip():
                    customer_segments.append({
                        'index': idx,
                        'start_time': seg_input.start_time,
                        'end_time': seg_input.end_time,
                        'text': seg_input.text.strip()
                    })
        
        if not customer_segments:
            logger.warning(f"세션 {session_id}: 고객 발화가 없습니다.")
            return {
                "status": "success",
                "session_id": session_id,
                "processed_customer_turns": 0,
                "skipped_turns": 0,
                "error_turns": 0,
                "generated_solutions": 0
            }
        
        # 개별 세그먼트 단위로 파이프라인 실행
        # 주의: process_single_sentence는 문장 분리를 하지 않지만,
        # process는 문장 분리를 하므로 결과 수가 다를 수 있음
        # 따라서 각 세그먼트를 개별적으로 process_single_sentence로 처리
        pipeline_results = []
        segment_to_results_map = {}  # seg_idx -> [result_indices] 매핑
        
        for seg_idx, seg_data in enumerate(customer_segments):
            try:
                # 단일 세그먼트 처리 (문장 분리 없이 전체 텍스트 처리)
                classification_result = pipeline.process_single_sentence(
                    seg_data['text'],
                    session_id
                )
                # Intensity 정보 디버깅
                intensity = getattr(classification_result, 'intensity', None)
                intensity_level = getattr(classification_result, 'intensity_level', None)
                if intensity is not None or intensity_level is not None:
                    logger.info(f"세그먼트 {seg_idx} Intensity 정보: intensity={intensity}, level={intensity_level}, label={classification_result.label}")
                else:
                    logger.debug(f"세그먼트 {seg_idx} Intensity 정보 없음: label={classification_result.label}, label_type={classification_result.label_type}")
                
                # segment_map에 저장 (pipeline_results 인덱스 기준)
                result_idx = len(pipeline_results)
                segment_map[result_idx] = seg_data
                segment_to_results_map[seg_idx] = [result_idx]  # 하나의 세그먼트는 하나의 결과
                pipeline_results.append(classification_result)
                logger.debug(f"세그먼트 {seg_idx} 처리 완료: {seg_data['text'][:50]}... -> 결과 인덱스 {result_idx}")
            except Exception as e:
                logger.error(f"세그먼트 {seg_idx} 처리 실패: {e}", exc_info=True)
                continue
        
        # PipelineResult 형식으로 변환
        from .logic_classify_system.data.data_structures import PipelineResult
        from datetime import datetime
        pipeline_result = PipelineResult(
            session_id=session_id,
            results=pipeline_results,
            timestamp=datetime.now()
        )
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
    # 주의: result_idx는 pipeline_result.results의 인덱스이고,
    # segment_map[result_idx]는 해당 결과에 대응하는 세그먼트 정보
    for result_idx, classification_result in enumerate(pipeline_result.results):
        
        try:
            origin_info = segment_map.get(result_idx)
            if not origin_info:
                logger.warning(f"결과 인덱스 {result_idx}: segment_map에 매핑 정보가 없습니다. 건너뜁니다.")
                continue
                
            target_start_time = origin_info.get('start_time')
            if target_start_time is None:
                logger.warning(f"결과 인덱스 {result_idx}: start_time이 None입니다. 건너뜁니다.")
                continue

            text = origin_info.get('text','')

            # start_time으로 정확히 매칭 (부동소수점 오차 고려)
            segment = None
            for seg in db_segments:
                if abs(seg.start_time - target_start_time) < 0.01:  # 0.01초 이내 차이 허용
                    segment = seg
                    break
            
            # 정확한 매칭 실패 시 가장 가까운 세그먼트 찾기
            if not segment:
                logger.warning(f"결과 인덱스 {result_idx}: start_time={target_start_time}로 정확히 매칭되는 세그먼트를 찾을 수 없습니다.")
                # 가장 가까운 세그먼트 찾기
                min_diff = float('inf')
                closest_seg = None
                for seg in db_segments:
                    diff = abs(seg.start_time - target_start_time) if target_start_time else float('inf')
                    if diff < min_diff:
                        min_diff = diff
                        closest_seg = seg
                
                if closest_seg and min_diff < 1.0:  # 1초 이내 차이면 허용
                    segment = closest_seg
                    logger.info(f"결과 인덱스 {result_idx}: 가장 가까운 세그먼트 사용 (차이: {min_diff:.3f}초)")
                else:
                    logger.error(f"결과 인덱스 {result_idx}: 매칭 가능한 세그먼트가 없습니다. 건너뜁니다.")
                    continue
            
            emotion_label = segment.emotion_label or "중립"
            
            if not segment.emotion_label:
                logger.debug(f"Segment {segment.id}: emotion_label 없음, 기본값 '중립' 사용")
            
            # 세 번째 세션에서 계산된 최종 점수 사용
            # classification_result.metadata에 final_scores가 포함되어 있음
            final_scores = None
            if hasattr(classification_result, 'metadata') and classification_result.metadata:
                final_scores = classification_result.metadata.get('final_scores')
            
            # 최종 점수가 없으면 재계산 시도
            if not final_scores:
                logger.warning(f"Segment {segment.id}: 최종 점수가 metadata에 없습니다. 재계산 시도...")
                try:
                    # final_score_session을 사용하여 재계산
                    from .logic_classify_system.pipeline.final_score_calculation_session import FinalScoreCalculationSession
                    final_score_session = FinalScoreCalculationSession(
                        use_feature_extractor=True,
                        profanity_detector=pipeline.profanity_detector if hasattr(pipeline, 'profanity_detector') else None
                    )
                    final_scores_dict = final_score_session.calculate_final_scores(
                        classification_result=classification_result,
                        text=text
                    )
                    final_scores = {
                        'score_risk': final_scores_dict.get('score_risk', 0.0),
                        'score_profanity': final_scores_dict.get('score_profanity', 0.0),
                        'score_threat': final_scores_dict.get('score_threat', 0.0),
                        'score_unreasonable_demand': final_scores_dict.get('score_unreasonable_demand', 0.0),
                        'score_sexual_harassment': final_scores_dict.get('score_sexual_harassment', 0.0),
                        'score_hate_speech': final_scores_dict.get('score_hate_speech', 0.0),
                        'score_repetition': final_scores_dict.get('score_repetition', 0.0),
                    }
                    logger.info(f"Segment {segment.id}: final_scores 재계산 완료. score_profanity={final_scores.get('score_profanity', 0.0):.2f}")
                except Exception as e:
                    logger.error(f"Segment {segment.id}: final_scores 재계산 실패: {e}", exc_info=True)
                    final_scores = {
                        'score_risk': 0.0,
                        'score_profanity': 0.0,
                        'score_threat': 0.0,
                        'score_unreasonable_demand': 0.0,
                        'score_sexual_harassment': 0.0,
                        'score_hate_speech': 0.0,
                        'score_repetition': 0.0
                    }
            
            # 욕설 감지 여부 확인 (final_scores 기반 + classification_result 확인)
            score_profanity = final_scores.get('score_profanity', 0.0)
            is_profanity = score_profanity > 0.0
            
            # classification_result의 label이 PROFANITY인 경우도 확인
            if not is_profanity and classification_result.label == "PROFANITY":
                is_profanity = True
                score_profanity = max(score_profanity, classification_result.confidence or 0.0)
                logger.debug(f"Segment {segment.id}: label이 PROFANITY이므로 욕설로 처리. score_profanity={score_profanity:.2f}")
            
            profanity_category = None
            profanity_method = None
            if is_profanity:
                profanity_category = "PROFANITY"
                profanity_method = "baseline"
                logger.debug(f"Segment {segment.id}: 욕설 감지됨. score_profanity={score_profanity:.2f}, text={text[:50]}")
            
            # 상세 정보 (안전한 속성 접근) - 먼저 가져오기
            intensity = getattr(classification_result, 'intensity', None)
            intensity_level = getattr(classification_result, 'intensity_level', None)
            is_immoral = getattr(classification_result, 'is_immoral', False)
            immorality_confidence = getattr(classification_result, 'immorality_confidence', 0.0)
            
            # Intensity 정보 디버깅
            if intensity is not None or intensity_level is not None:
                logger.info(f"Segment {segment.id} DB 저장 시 Intensity 정보: intensity={intensity}, level={intensity_level}")
            else:
                logger.debug(f"Segment {segment.id} DB 저장 시 Intensity 정보 없음: label={classification_result.label}, label_type={classification_result.label_type}")
            
            # extracted_features: solution_system 호환성을 위해 metadata에서 가져오기
            extracted_features = (
                classification_result.metadata.get('extracted_features', {})
                if hasattr(classification_result, 'metadata') and classification_result.metadata
                else {}
            )
            
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
                    
                    # 욕설 감지 결과
                    'is_profanity': is_profanity,
                    'profanity_category': profanity_category,
                    'profanity_method': profanity_method,
                    
                    # 최종 점수 계산 결과 (세 번째 세션에서 계산된 점수 사용)
                    'score_risk': _validate_score(final_scores.get('score_risk', 0.0), 'score_risk'),
                    'score_profanity': _validate_score(score_profanity, 'score_profanity'),  # 재계산된 값 사용
                    'score_threat': _validate_score(final_scores.get('score_threat', 0.0), 'score_threat'),
                    'score_unreasonable_demand': _validate_score(final_scores.get('score_unreasonable_demand', 0.0), 'score_unreasonable_demand'),
                    'score_sexual_harassment': _validate_score(final_scores.get('score_sexual_harassment', 0.0), 'score_sexual_harassment'),
                    'score_hate_speech': _validate_score(final_scores.get('score_hate_speech', 0.0), 'score_hate_speech'),
                    'score_repetition': _validate_score(final_scores.get('score_repetition', 0.0), 'score_repetition'),
                    
                    # 상세 정보 (Intensity + AI Hub 모델 결과 포함)
                    'feature_scores_extra': {
                        # Intensity 모델 결과
                        'intensity': intensity,
                        'intensity_level': intensity_level,
                        'is_immoral': is_immoral,
                        'immorality_confidence': immorality_confidence,
                        # AI Hub 모델 결과
                        'aihub_is_immoral': aihub_is_immoral,
                        'aihub_confidence': aihub_confidence,
                        'aihub_type': aihub_type,
                        'aihub_type_confidence': aihub_type_confidence
                    },
                    'extracted_features': extracted_features,
                    
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