"""
'감사합니다. 좋은 서비스였어요'가 VIOLENCE_THREAT로 분류되는 원인 분석
"""
import os
import sys
import django
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')
django.setup()

from logical_analysis.logic_classify_system.pipeline.baseline_validation_session import BaselineValidationSession
from logical_analysis.logic_classify_system.intent_classifier.baseline_rules import IntentBaselineRules

def test_baseline_rules():
    """Baseline 규칙 테스트"""
    print("=" * 60)
    print("Baseline 규칙 테스트")
    print("=" * 60)
    
    text = "감사합니다. 좋은 서비스였어요"
    print(f"\n테스트 텍스트: {text}")
    
    baseline_rules = IntentBaselineRules()
    results = baseline_rules.detect_special_labels(text, session_context=None, return_type="list")
    
    print(f"\nBaseline 규칙 결과: {results}")
    
    if results:
        print("⚠️ Baseline 규칙에서 Special Label 감지됨!")
        for label, confidence in results:
            print(f"  - {label}: {confidence:.4f}")
    else:
        print("✅ Baseline 규칙에서 Special Label 감지 안 됨 (정상)")
    
    return results

def test_baseline_validation_session():
    """BaselineValidationSession 테스트"""
    print("\n" + "=" * 60)
    print("BaselineValidationSession 테스트")
    print("=" * 60)
    
    text = "감사합니다. 좋은 서비스였어요"
    print(f"\n테스트 텍스트: {text}")
    
    # AI hub 모델 없이 테스트
    session = BaselineValidationSession(
        aihub_model=None,
        aihub_base_path=None
    )
    
    result = session.validate(
        text=text,
        session_context=None,
        profanity_detected=False,
        profanity_category=None,
        profanity_confidence=0.0
    )
    
    print(f"\n분류 결과:")
    print(f"  - Label: {result.label}")
    print(f"  - Label Type: {result.label_type}")
    print(f"  - Confidence: {result.confidence:.4f}")
    print(f"  - Probabilities: {result.probabilities}")
    
    if result.label == "VIOLENCE_THREAT":
        print("\n❌ 문제 발견: VIOLENCE_THREAT로 잘못 분류됨!")
    elif result.label_type == "SPECIAL":
        print(f"\n⚠️ Special Label로 분류됨: {result.label}")
    else:
        print("\n✅ Normal Label로 정상 분류됨")
    
    return result

def test_with_aihub_model():
    """AI hub 모델이 있는 경우 테스트"""
    print("\n" + "=" * 60)
    print("AI hub 모델 테스트 (있는 경우)")
    print("=" * 60)
    
    text = "감사합니다. 좋은 서비스였어요"
    print(f"\n테스트 텍스트: {text}")
    
    from logical_analysis.logic_classify_system.config.model_paths import get_aihub_base_model_path
    from logical_analysis.logic_classify_system.models.aihub_ethic_model import AIHubEthicModel
    
    aihub_base_path = get_aihub_base_model_path()
    
    if aihub_base_path and Path(aihub_base_path).exists():
        print(f"\nAI hub 모델 경로: {aihub_base_path}")
        try:
            aihub_model = AIHubEthicModel(base_model_path=aihub_base_path)
            
            # 모델 1: is_immoral 판단
            is_immoral, confidence = aihub_model.predict_immoral(text)
            print(f"\nAI hub 모델 1 (is_immoral):")
            print(f"  - is_immoral: {is_immoral}")
            print(f"  - confidence: {confidence:.4f}")
            
            if is_immoral:
                # 모델 2: 비도덕 유형 분류
                aihub_type = aihub_model.predict_type(text)
                type_confidence = aihub_model.get_confidence(text, aihub_type)
                print(f"\nAI hub 모델 2 (type):")
                print(f"  - type: {aihub_type}")
                print(f"  - confidence: {type_confidence:.4f}")
                
                if aihub_type == "VIOLENCE":
                    print("\n❌ 문제 발견: AI hub 모델이 VIOLENCE로 잘못 분류함!")
                else:
                    print(f"\n✅ AI hub 모델 분류: {aihub_type}")
            else:
                print("\n✅ AI hub 모델: is_immoral=False (정상)")
        except Exception as e:
            print(f"\n⚠️ AI hub 모델 테스트 실패: {e}")
    else:
        print("\n⚠️ AI hub 모델 경로를 찾을 수 없습니다.")

if __name__ == "__main__":
    # 1. Baseline 규칙 테스트
    baseline_results = test_baseline_rules()
    
    # 2. BaselineValidationSession 테스트 (AI hub 모델 없이)
    result = test_baseline_validation_session()
    
    # 3. AI hub 모델 테스트 (있는 경우)
    test_with_aihub_model()
    
    print("\n" + "=" * 60)
    print("분석 완료")
    print("=" * 60)

