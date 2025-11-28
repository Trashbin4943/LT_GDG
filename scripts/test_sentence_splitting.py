"""
문장 분리 테스트 - 파이프라인이 세그먼트를 어떻게 분리하는지 확인
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

# 테스트 텍스트들
test_texts = [
    "시발놈아! 이게 뭐야? 죽여버릴거야!",
    "이 상품의 배송 일정을 알려주세요. 언제 도착하나요?",
    "서비스가 너무 불만족스럽습니다. 환불해주세요."
]

print("=" * 80)
print("문장 분리 테스트")
print("=" * 80)

# TextSplitter 테스트
text_splitter = TextSplitter()
for text in test_texts:
    print(f"\n원본 텍스트: {text}")
    customer_sentences, agent_sentences = text_splitter.split_by_speaker(text)
    print(f"  분리된 고객 문장 수: {len(customer_sentences)}")
    for idx, sent in enumerate(customer_sentences):
        print(f"    [{idx}] {sent}")

print("\n" + "=" * 80)
print("process_single_sentence 테스트")
print("=" * 80)

# process_single_sentence 테스트
for text in test_texts:
    print(f"\n원본 텍스트: {text}")
    result = pipeline.process_single_sentence(text, "test-session")
    print(f"  결과 라벨: {result.label}")
    print(f"  결과 텍스트: {result.text}")
    
    # 파이프라인 내부에서 어떻게 분리되는지 확인
    customer_sentences, agent_sentences = text_splitter.split_by_speaker(text)
    print(f"  내부 분리 결과: {len(customer_sentences)}개 문장")
    for idx, sent in enumerate(customer_sentences):
        print(f"    [{idx}] {sent}")

print("\n" + "=" * 80)
print("process 메서드 테스트 (합쳐서 처리)")
print("=" * 80)

# 합쳐서 처리
combined_text = " ".join(test_texts)
print(f"\n합쳐진 텍스트: {combined_text}")
result = pipeline.process(combined_text, "test-session")
print(f"  결과 수: {len(result.results)}")
for idx, res in enumerate(result.results):
    print(f"  [{idx}] {res.text[:50]}... -> {res.label}")

