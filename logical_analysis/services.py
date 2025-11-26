from django.db import transaction
from django.utils import timezone

# 1. Pipeline Import
from .logic_classify_system.pipeline.main_pipeline import MainPipeline

# 2. Models Import (SpeakerSegment는 audio_process 앱, Result는 현재 앱)
from audio_process.models import SpeakerSegment, CallRecording
from .models import CustomerAnalysisResult
from .schemas import SessionAnalysisRequest

@transaction.atomic
def analyze_and_save_customer_turns(request_data: SessionAnalysisRequest):
    """
    세션 데이터를 받아 파이프라인을 실행하고, '고객(Customer)' 분석 결과만 DB에 저장합니다.
    """
    
    # 1. 파이프라인 실행
    # Pydantic 모델을 dict로 변환하여 파이프라인에 전달
    pipeline = MainPipeline()
    pipeline_result = pipeline.process(request_data.model_dump())
    
    session_id = pipeline_result.session_id
    saved_count = 0

    try:
        recording_obj = CallRecording.objects.get(session_id=str(session_id))
    except CallRecording.DoesNotExist:
        raise ValueError(f"Session ID {str(session_id)} not found in CallRecording.")

    # 2. 결과 순회 및 저장
    for turn_res in pipeline_result.turn_results:
        
        # Customer Result가 존재하는 경우만 처리 (Agent 무시)
        if turn_res.customer_result:
            c_res = turn_res.customer_result
            turn_index = turn_res.turn_index
            timestamp = timezone.now()

            # (1) 부모 세그먼트 저장/조회 (audio_process 앱)
            # speaker='customer'인 세그먼트만 대상이 됩니다.
            segment, created = SpeakerSegment.objects.get_or_create(
                session_id=recording_obj,
                turn_index=turn_index,
                defaults={
                    'text': c_res.text,
                    'speaker_label':'customer',
                    'start_time': 0.0,
                    'end_time': 0.0
                    # 만약 SpeakerSegment 모델에 speaker 필드가 있다면 'customer'로 저장
                }
            )

            # (2) 고객 분석 결과 저장 (logical_analysis 앱)
            # MainPipeline의 Output 구조에 맞춰 필드 매핑
            CustomerAnalysisResult.objects.update_or_create(
                segment=segment,
                defaults={
                    # 분류 결과
                    'label': c_res.classification_result.label,
                    'label_type': c_res.classification_result.label_type,
                    'classification_confidence': c_res.classification_result.confidence,
                    'classification_probabilities': c_res.classification_result.probabilities or {},

                    # 욕설 감지 결과
                    'is_profanity': c_res.profanity_result.is_profanity,
                    'profanity_category': c_res.profanity_result.category,
                    
                    # 주요 리스크 점수 (Flattened Columns)
                    'score_risk': turn_res.turn_scores.get('turn_risk_score', 0.0), # 종합 리스크
                    'score_profanity': c_res.feature_scores.get('profanity_score', 0.0),
                    'score_threat': c_res.feature_scores.get('threat_score', 0.0),
                    'score_unreasonable_demand': c_res.feature_scores.get('unreasonable_demand_score', 0.0),
                    
                    'score_sexual_harassment': c_res.feature_scores.get('sexual_harassment_score', 0.0),
                    'score_hate_speech': c_res.feature_scores.get('hate_speech_score', 0.0),
                    'score_repetition': c_res.feature_scores.get('repetition_keyword_score', 0.0),

                    # 나머지 상세 정보 (JSON Fields)
                    # 모델에 정의된 feature_scores_extra에 모든 점수 덤프
                    'feature_scores_extra': c_res.feature_scores,
                    'extracted_features': c_res.extracted_features,
                    
                    'analyzed_at': timestamp
                }
            )
            saved_count += 1
            
    return {
        "status": "success",
        "session_id": str(session_id),
        "processed_customer_turns": saved_count
    }