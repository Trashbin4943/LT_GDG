"""
Enhanced Intent Predictor 상세 테스트
모든 발화에 대해 intensity 정보가 수집되는지 확인
"""
import os
import sys
import django
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')
django.setup()

from logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor
from logical_analysis.logic_classify_system.config.model_paths import get_intensity_model_path, get_ternary_model_path

def test_all_utterances():
    """모든 발화에 대해 intensity 정보 수집 확인"""
    print("=" * 60)
    print("Enhanced Intent Predictor 상세 테스트")
    print("=" * 60)
    print()
    
    predictor = EnhancedIntentPredictor(
        intensity_model_path=get_intensity_model_path(),
        ternary_model_path=get_ternary_model_path(),
        use_models=True
    )
    
    test_cases = [
        ("안녕하세요. 문의사항이 있습니다.", False, "Normal 발화"),
        ("이런 서비스는 말이 안 됩니다!", False, "Special 발화 (무리한 요구)"),
        ("시발 이게 뭔 소리야!", True, "Special 발화 (욕설)"),
    ]
    
    for text, profanity_detected, description in test_cases:
        print(f"테스트 케이스: {description}")
        print(f"텍스트: {text}")
        print(f"욕설 감지: {profanity_detected}")
        print("-" * 60)
        
        result = predictor.predict(
            text=text,
            profanity_detected=profanity_detected,
            session_context=None
        )
        
        print(f"Label: {result.label}")
        print(f"Label Type: {result.label_type}")
        print(f"Confidence: {result.confidence:.4f}")
        
        # Intensity 정보 확인
        intensity = getattr(result, 'intensity', None)
        intensity_level = getattr(result, 'intensity_level', None)
        is_immoral = getattr(result, 'is_immoral', None)
        
        print(f"Intensity: {intensity}")
        print(f"Intensity Level: {intensity_level}")
        print(f"Is Immoral: {is_immoral}")
        
        # 검증
        if intensity is not None:
            if 0.0 <= intensity <= 3.0:
                print("✅ Intensity 값이 올바른 범위에 있습니다 (0.0 ~ 3.0)")
            else:
                print(f"⚠️ Intensity 값이 범위를 벗어났습니다: {intensity}")
        else:
            print("❌ Intensity 정보가 없습니다!")
        
        if intensity_level:
            expected_levels = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
            if intensity_level in expected_levels:
                print(f"✅ Intensity Level이 올바른 값입니다: {intensity_level}")
            else:
                print(f"⚠️ Intensity Level이 예상과 다릅니다: {intensity_level}")
        else:
            print("❌ Intensity Level 정보가 없습니다!")
        
        print()
    
    print("=" * 60)
    print("✅ 모든 발화에 대해 intensity 정보가 수집되었는지 확인 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_all_utterances()

