"""
매핑 문제 상세 테스트
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
from logical_analysis.logic_classify_system.preprocessing.text_splitter import TextSplitter

# 파이프라인 초기화
intensity_model_path = get_intensity_model_path()
ternary_model_path = get_ternary_model_path()

pipeline = MainPipeline(
    intensity_model_path=intensity_model_path,
    ternary_model_path=ternary_model_path,
    use_two_stage_session=True
)

text_splitter = TextSplitter()

# 실제 세그먼트 텍스트들
test_segments = [
    "이 상품의 배송 일정을 알려주세요. 언제 도착하나요?",
    "서비스가 너무 불만족스럽습니다. 환불해주세요.",
    "배송이 너무 늦었어요. 약속한 날짜에 도착하지 않았습니다.",
    "시발놈아! 이게 뭐야? 죽여버릴거야!",
    "찾아가서 끝장낼거야! 참교육 해줄거야!",
]

print("=" * 80)
print("매핑 문제 상세 테스트")
print("=" * 80)

print("\n1. 각 세그먼트를 process_single_sentence로 처리:")
results_single = []
for idx, text in enumerate(test_segments):
    print(f"\n  세그먼트 [{idx}]: {text[:50]}...")
    
    # 문장 분리 확인
    customer_sentences, _ = text_splitter.split_by_speaker(text)
    print(f"    분리된 문장 수: {len(customer_sentences)}")
    for i, sent in enumerate(customer_sentences):
        print(f"      [{i}] {sent}")
    
    # process_single_sentence 호출
    result = pipeline.process_single_sentence(text, "test-session")
    results_single.append(result)
    print(f"    결과: label={result.label}, text={result.text[:50]}...")

print(f"\n  총 결과 수: {len(results_single)}")

print("\n2. 합쳐서 process로 처리:")
combined = " ".join(test_segments)
print(f"  합쳐진 텍스트: {combined[:100]}...")
result_combined = pipeline.process(combined, "test-session")
print(f"  결과 수: {len(result_combined.results)}")
for idx, res in enumerate(result_combined.results):
    print(f"    [{idx}] {res.text[:50]}... -> {res.label}")

print("\n3. 비교:")
print(f"  process_single_sentence 결과 수: {len(results_single)} (예상: {len(test_segments)})")
print(f"  process 결과 수: {len(result_combined.results)} (예상: 분리된 문장 수)")

# 문장 분리 총 개수 계산
total_sentences = 0
for text in test_segments:
    customer_sentences, _ = text_splitter.split_by_speaker(text)
    total_sentences += len(customer_sentences)

print(f"  분리된 총 문장 수: {total_sentences}")
print(f"  process 결과 수와 일치: {len(result_combined.results) == total_sentences}")

print("\n4. 문제 분석:")
print("  - process_single_sentence는 각 세그먼트를 하나의 결과로 반환")
print("  - 하지만 내부에서 문장 분리가 일어나면 첫 번째 문장만 처리되거나 전체를 합쳐서 처리")
print("  - process는 모든 분리된 문장에 대해 결과를 반환")
print("  - 따라서 process_single_sentence를 여러 번 호출하면 결과 수가 맞지 않을 수 있음")

