"""
Intensity 정보 저장 테스트
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

# 파이프라인 초기화
intensity_model_path = get_intensity_model_path()
ternary_model_path = get_ternary_model_path()

pipeline = MainPipeline(
    intensity_model_path=intensity_model_path,
    ternary_model_path=ternary_model_path,
    use_two_stage_session=True
)

# 테스트 텍스트
test_text = "시발놈아! 이게 뭐야?"

print(f"테스트 텍스트: {test_text}")
print("\n" + "="*60)

# process_single_sentence 호출
result = pipeline.process_single_sentence(test_text, "test-session")

print(f"\n결과:")
print(f"  라벨: {result.label}")
print(f"  라벨 타입: {result.label_type}")
print(f"  신뢰도: {result.confidence}")

# Intensity 정보 확인
intensity = getattr(result, 'intensity', None)
intensity_level = getattr(result, 'intensity_level', None)
is_immoral = getattr(result, 'is_immoral', None)
immorality_confidence = getattr(result, 'immorality_confidence', None)

print(f"\nIntensity 정보:")
print(f"  intensity: {intensity}")
print(f"  intensity_level: {intensity_level}")
print(f"  is_immoral: {is_immoral}")
print(f"  immorality_confidence: {immorality_confidence}")

# metadata 확인
if hasattr(result, 'metadata') and result.metadata:
    print(f"\nMetadata:")
    print(f"  keys: {list(result.metadata.keys())}")
    if 'final_scores' in result.metadata:
        print(f"  final_scores: {result.metadata['final_scores']}")
else:
    print(f"\nMetadata: 없음")

# 속성 목록 확인
print(f"\nClassificationResult 속성:")
attrs = [attr for attr in dir(result) if not attr.startswith('_')]
for attr in attrs:
    try:
        value = getattr(result, attr)
        if not callable(value):
            print(f"  {attr}: {type(value).__name__} = {value}")
    except:
        pass

