"""
Django 서버 환경에서 모델 동작 테스트
"""
import os
import sys
import django
from pathlib import Path

# Django 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')
django.setup()

from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)
from logical_analysis.logic_classify_system.models.intensity_regression_model import IntensityRegressionModel
from logical_analysis.logic_classify_system.models.ternary_classification_model import TernaryClassificationModel
from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.services import analyze_and_save_customer_turns
from logical_analysis.schemas import SessionAnalysisRequest, SegmentInput

def test_model_paths():
    """모델 경로 테스트"""
    print("=== 1. 모델 경로 테스트 ===\n")
    
    intensity_path = get_intensity_model_path()
    ternary_path = get_ternary_model_path()
    
    print(f"Intensity Model Path: {intensity_path}")
    print(f"Ternary Model Path: {ternary_path}\n")
    
    if not intensity_path or not ternary_path:
        print("❌ 모델 경로를 찾을 수 없습니다.")
        return False
    
    print("✅ 모델 경로 확인 완료\n")
    return True

def test_model_loading():
    """모델 로드 테스트"""
    print("=== 2. 모델 로드 테스트 ===\n")
    
    intensity_path = get_intensity_model_path()
    ternary_path = get_ternary_model_path()
    
    # Intensity Regression Model
    print("Intensity Regression Model 로드 중...")
    try:
        intensity_model = IntensityRegressionModel(intensity_path)
        if not intensity_model.is_available():
            print("❌ Intensity 모델을 로드할 수 없습니다.")
            return False
        print("✅ Intensity 모델 로드 성공")
        
        # 테스트 예측
        test_result = intensity_model.predict("테스트 문장입니다.")
        print(f"   예측 결과: intensity={test_result['intensity']:.4f}, is_immoral={test_result['is_immoral']}")
        
        # 범위 확인
        if 0.0 <= test_result['intensity'] <= 3.0:
            print(f"   ✅ Intensity 값이 올바른 범위에 있습니다 (0.0 ~ 3.0)")
        else:
            print(f"   ⚠️ Intensity 값이 범위를 벗어났습니다: {test_result['intensity']}")
    except Exception as e:
        print(f"❌ Intensity 모델 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Ternary Classification Model
    print("\nTernary Classification Model 로드 중...")
    try:
        ternary_model = TernaryClassificationModel(ternary_path)
        if not ternary_model.is_available():
            print("❌ Ternary 모델을 로드할 수 없습니다.")
            return False
        print("✅ Ternary 모델 로드 성공")
        
        # 테스트 예측
        test_result = ternary_model.predict("테스트 문장입니다.")
        print(f"   예측 결과: level={test_result['intensity_level']}, confidence={test_result['intensity_level_confidence']:.4f}")
        print(f"   확률 분포: {test_result['probabilities']}")
        
        # 4가지 분류 확인
        expected_labels = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
        if test_result['intensity_level'] in expected_labels:
            print(f"   ✅ Intensity Level이 올바른 값입니다")
        if all(label in test_result['probabilities'] for label in expected_labels):
            print(f"   ✅ 모든 확률 값이 포함되어 있습니다")
    except Exception as e:
        print(f"❌ Ternary 모델 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ 모델 로드 테스트 완료\n")
    return True

def test_pipeline():
    """파이프라인 테스트"""
    print("=== 3. 파이프라인 테스트 ===\n")
    
    intensity_path = get_intensity_model_path()
    ternary_path = get_ternary_model_path()
    
    try:
        pipeline = MainPipeline(
            intensity_model_path=intensity_path,
            ternary_model_path=ternary_path,
            use_enhanced_predictor=True
        )
        print("✅ 파이프라인 초기화 성공")
        
        # 테스트 텍스트
        test_text = "안녕하세요. 문의사항이 있습니다."
        print(f"\n테스트 텍스트: {test_text}")
        
        result = pipeline.process(test_text, session_id="test_session")
        print(f"처리된 결과 수: {len(result.results)}")
        
        if result.results:
            first_result = result.results[0]
            print(f"첫 번째 결과:")
            print(f"  - Label: {first_result.label}")
            print(f"  - Label Type: {first_result.label_type}")
            print(f"  - Confidence: {first_result.confidence:.4f}")
            if hasattr(first_result, 'intensity') and first_result.intensity is not None:
                print(f"  - Intensity: {first_result.intensity:.4f}")
            if hasattr(first_result, 'intensity_level') and first_result.intensity_level:
                print(f"  - Intensity Level: {first_result.intensity_level}")
        
        print("\n✅ 파이프라인 테스트 완료\n")
        return True
    except Exception as e:
        print(f"❌ 파이프라인 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_predictor():
    """Enhanced Intent Predictor 테스트"""
    print("=== 4. Enhanced Intent Predictor 테스트 ===\n")
    
    from logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor
    from logical_analysis.logic_classify_system.config.model_paths import (
        get_intensity_model_path,
        get_ternary_model_path
    )
    
    intensity_path = get_intensity_model_path()
    ternary_path = get_ternary_model_path()
    
    try:
        predictor = EnhancedIntentPredictor(
            intensity_model_path=intensity_path,
            ternary_model_path=ternary_path,
            use_models=True
        )
        print("✅ Enhanced Intent Predictor 초기화 성공")
        
        # 테스트 케이스들
        test_cases = [
            ("안녕하세요. 문의사항이 있습니다.", False),  # Normal
            ("이런 서비스는 말이 안 됩니다!", False),  # Special 가능성
        ]
        
        for text, profanity_detected in test_cases:
            print(f"\n테스트 텍스트: {text}")
            result = predictor.predict(
                text=text,
                profanity_detected=profanity_detected,
                session_context=None
            )
            print(f"  - Label: {result.label}")
            print(f"  - Label Type: {result.label_type}")
            print(f"  - Confidence: {result.confidence:.4f}")
            if hasattr(result, 'intensity') and result.intensity is not None:
                print(f"  - Intensity: {result.intensity:.4f}")
            if hasattr(result, 'intensity_level') and result.intensity_level:
                print(f"  - Intensity Level: {result.intensity_level}")
        
        print("\n✅ Enhanced Intent Predictor 테스트 완료\n")
        return True
    except Exception as e:
        print(f"❌ Enhanced Intent Predictor 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Django 서버 환경에서 모델 동작 테스트")
    print("=" * 60)
    print()
    
    results = []
    
    # 1. 모델 경로 테스트
    results.append(("모델 경로", test_model_paths()))
    
    # 2. 모델 로드 테스트
    results.append(("모델 로드", test_model_loading()))
    
    # 3. 파이프라인 테스트
    results.append(("파이프라인", test_pipeline()))
    
    # 4. Enhanced Intent Predictor 테스트
    results.append(("Enhanced Predictor", test_enhanced_predictor()))
    
    # 결과 요약
    print("=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
        sys.exit(0)
    else:
        print("\n⚠️ 일부 테스트 실패")
        sys.exit(1)

