"""
논리분석 문제 진단 스크립트

DB에 저장된 데이터와 파이프라인 처리 결과를 비교하여 문제를 진단합니다.
"""

import os
import sys
from pathlib import Path

# Django 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from audio_process.models import CallRecording, SpeakerSegment
from logical_analysis.models import CustomerAnalysisResult
from logical_analysis.logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)
from logical_analysis.logic_classify_system.models import AIHUB_MODEL_DIR


def test_profanity_detection():
    """욕설 감지 테스트"""
    print("=" * 60)
    print("1. 욕설 감지 테스트")
    print("=" * 60)
    
    detector = ProfanityDetector(use_korcen=False)
    
    test_texts = [
        "시발놈아! 이게 뭐야?",
        "시발",
        "개새끼",
        "죽여버릴거야",
        "안녕하세요"
    ]
    
    for text in test_texts:
        result = detector.detect(text)
        print(f"\n텍스트: {text}")
        print(f"  욕설 감지: {result.is_profanity}")
        print(f"  카테고리: {result.category}")
        print(f"  신뢰도: {result.confidence}")
        print(f"  방법: {result.method}")


def check_db_results(session_id: str = None):
    """DB에 저장된 결과 확인"""
    print("\n" + "=" * 60)
    print("2. DB 저장 결과 확인")
    print("=" * 60)
    
    if session_id:
        recordings = CallRecording.objects.filter(session_id=session_id)
    else:
        recordings = CallRecording.objects.all().order_by('-created_at')[:5]
    
    if not recordings.exists():
        print("❌ 저장된 CallRecording이 없습니다.")
        return
    
    for recording in recordings:
        print(f"\n📋 세션 ID: {recording.session_id}")
        print(f"   생성일: {recording.created_at}")
        
        # 고객 세그먼트 확인
        customer_segments = SpeakerSegment.objects.filter(
            session_id=recording,
            speaker_label__in=['customer', 'client']
        )
        print(f"   고객 발화 수: {customer_segments.count()}")
        
        # 분석 결과 확인
        analysis_results = CustomerAnalysisResult.objects.filter(
            segment__session_id=recording
        ).select_related('segment')
        
        print(f"   분석 결과 수: {analysis_results.count()}")
        
        # 욕설이 포함된 발화 확인
        profanity_results = analysis_results.filter(is_profanity=True)
        print(f"   욕설 감지된 발화: {profanity_results.count()}")
        
        if profanity_results.exists():
            print("\n   ⚠️ 욕설 감지된 발화:")
            for res in profanity_results[:5]:
                print(f"      - [{res.label}] {res.segment.text[:50]}...")
                print(f"        위험도: {res.score_risk:.2f}, 욕설 점수: {res.score_profanity:.2f}")
                print(f"        카테고리: {res.profanity_category}, 방법: {res.profanity_method}")
        
        # '시발'이 포함된 발화 확인
        segments_with_profanity = customer_segments.filter(text__icontains='시발')
        if segments_with_profanity.exists():
            print(f"\n   🔍 '시발'이 포함된 발화: {segments_with_profanity.count()}개")
            for seg in segments_with_profanity:
                print(f"      - {seg.text[:80]}...")
                try:
                    analysis = CustomerAnalysisResult.objects.get(segment=seg)
                    print(f"        분석 결과: 욕설={analysis.is_profanity}, 점수={analysis.score_profanity:.2f}")
                except CustomerAnalysisResult.DoesNotExist:
                    print(f"        ❌ 분석 결과 없음!")
        
        # intensity 정보 확인
        results_with_intensity = analysis_results.exclude(
            feature_scores_extra__isnull=True
        ).exclude(feature_scores_extra={})
        
        print(f"\n   📊 Intensity 정보가 있는 결과: {results_with_intensity.count()}개")
        if results_with_intensity.exists():
            for res in results_with_intensity[:3]:
                intensity = res.feature_scores_extra.get('intensity')
                intensity_level = res.feature_scores_extra.get('intensity_level')
                print(f"      - {res.segment.text[:50]}...")
                print(f"        Intensity: {intensity}, Level: {intensity_level}")


def test_pipeline_processing(text: str, session_id: str = "test-diagnosis"):
    """파이프라인 처리 테스트"""
    print("\n" + "=" * 60)
    print("3. 파이프라인 처리 테스트")
    print("=" * 60)
    
    print(f"\n테스트 텍스트: {text}")
    
    try:
        # 파이프라인 초기화
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        # AI hub 모델 경로 설정 (환경 변수 또는 기본 경로)
        import os
        from pathlib import Path
        
        # AI hub 모델 경로
        aihub_base_path = os.getenv('AIHUB_BASE_MODEL_PATH') or str(AIHUB_MODEL_DIR)
        aihub_model1_checkpoint = os.getenv('AIHUB_MODEL1_CHECKPOINT')
        aihub_model2_checkpoint = os.getenv('AIHUB_MODEL2_CHECKPOINT')
        
        # AI hub 모델 경로 확인 및 출력
        print(f"\n📁 AI Hub 모델 경로 설정:")
        print(f"   base_path: {aihub_base_path}")
        print(f"   존재 여부: {Path(aihub_base_path).exists() if aihub_base_path else False}")
        print(f"   model1_checkpoint: {aihub_model1_checkpoint}")
        print(f"   model2_checkpoint: {aihub_model2_checkpoint}")
        
        pipeline = MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_two_stage_session=True,  # 새로운 두 단계 세션 구조 사용
            aihub_base_path=aihub_base_path if Path(aihub_base_path).exists() else None,
            aihub_model1_checkpoint=aihub_model1_checkpoint,
            aihub_model2_checkpoint=aihub_model2_checkpoint
        )
        
        # AI hub 모델 로드 상태 확인
        if hasattr(pipeline, 'baseline_session') and pipeline.baseline_session:
            aihub_status = pipeline.baseline_session.get_session_info().get('has_aihub_model', False)
            print(f"\n🤖 AI Hub 모델 로드 상태: {'✅ 로드됨' if aihub_status else '❌ 로드 안 됨'}")
        else:
            print(f"\n⚠️ BaselineSession이 초기화되지 않았습니다.")
        
        # 처리
        result = pipeline.process(text, session_id)
        
        print(f"\n✅ 처리 완료: {len(result.results)}개 결과")
        
        for idx, res in enumerate(result.results):
            print(f"\n   결과 {idx + 1}:")
            print(f"      텍스트: {res.text[:80]}...")
            print(f"      라벨: {res.label}")
            print(f"      라벨 타입: {res.label_type}")
            print(f"      신뢰도: {res.confidence:.2f}")
            
            # AI Hub 모델 사용 여부 확인
            # is_immoral과 immorality_confidence는 ClassificationResult 속성
            # aihub_type과 aihub_type_confidence는 metadata에 저장됨
            has_aihub_result = False
            if hasattr(res, 'is_immoral') and res.is_immoral is not None:
                has_aihub_result = True
                print(f"      🤖 AI Hub 모델 결과:")
                print(f"        - is_immoral: {res.is_immoral}")
                if hasattr(res, 'immorality_confidence'):
                    print(f"        - immorality_confidence: {res.immorality_confidence:.2f}")
            
            if hasattr(res, 'metadata') and res.metadata:
                aihub_type = res.metadata.get('aihub_type')
                aihub_type_confidence = res.metadata.get('aihub_type_confidence')
                
                if aihub_type:
                    if not has_aihub_result:
                        print(f"      🤖 AI Hub 모델 결과:")
                    print(f"        - type: {aihub_type}")
                    print(f"        - type_confidence: {aihub_type_confidence or 0.0:.2f}")
                    has_aihub_result = True
            
            if not has_aihub_result:
                print(f"      ⚠️ AI Hub 모델 결과 없음 (Baseline 규칙만 사용)")
            
            # metadata 확인
            if hasattr(res, 'metadata') and res.metadata:
                final_scores = res.metadata.get('final_scores')
                if final_scores:
                    print(f"      최종 점수:")
                    print(f"        - 위험도: {final_scores.get('score_risk', 0.0):.2f}")
                    print(f"        - 욕설: {final_scores.get('score_profanity', 0.0):.2f}")
                    print(f"        - 위협: {final_scores.get('score_threat', 0.0):.2f}")
                else:
                    print(f"      ⚠️ final_scores가 metadata에 없습니다!")
            else:
                print(f"      ⚠️ metadata가 없습니다!")
            
            # intensity 확인
            if hasattr(res, 'intensity'):
                print(f"      Intensity: {res.intensity}, Level: {res.intensity_level}")
            else:
                print(f"      ⚠️ Intensity 정보 없음")
                
    except Exception as e:
        print(f"\n❌ 파이프라인 처리 실패: {e}")
        import traceback
        traceback.print_exc()


def compare_segment_vs_combined():
    """개별 세그먼트 처리 vs 합쳐서 처리 비교"""
    print("\n" + "=" * 60)
    print("4. 개별 세그먼트 vs 합쳐서 처리 비교")
    print("=" * 60)
    
    # 예시 텍스트
    segments = [
        "안녕하세요",
        "시발놈아! 이게 뭐야?",
        "죽여버릴거야!"
    ]
    
    print("\n개별 세그먼트 처리:")
    detector = ProfanityDetector()
    for seg in segments:
        result = detector.detect(seg)
        print(f"  '{seg}' -> 욕설: {result.is_profanity}, 점수: {result.confidence:.2f}")
    
    print("\n합쳐서 처리:")
    combined = " ".join(segments)
    result = detector.detect(combined)
    print(f"  '{combined}' -> 욕설: {result.is_profanity}, 점수: {result.confidence:.2f}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='논리분석 문제 진단')
    parser.add_argument('--session-id', help='특정 세션 ID 확인')
    parser.add_argument('--test-text', help='테스트할 텍스트')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("논리분석 문제 진단 도구")
    print("=" * 60)
    
    # 1. 욕설 감지 테스트
    test_profanity_detection()
    
    # 2. DB 결과 확인
    check_db_results(args.session_id)
    
    # 3. 파이프라인 처리 테스트
    if args.test_text:
        test_pipeline_processing(args.test_text)
    else:
        test_pipeline_processing("시발놈아! 이게 뭐야? 죽여버릴거야!")
    
    # 4. 비교 테스트
    compare_segment_vs_combined()
    
    print("\n" + "=" * 60)
    print("진단 완료")
    print("=" * 60)


if __name__ == '__main__':
    main()

