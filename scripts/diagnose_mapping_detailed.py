"""
매핑 문제 상세 진단 - 실제 DB와 파이프라인 결과 비교
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from audio_process.models import CallRecording, SpeakerSegment
from logical_analysis.models import CustomerAnalysisResult
from logical_analysis.services import _convert_segments_to_request
from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

session_id = "a21cbea6-59ae-400e-bb4d-e75b0e18d9ed"

print("=" * 80)
print("매핑 문제 상세 진단")
print("=" * 80)

# 1. CallRecording 조회
recording = CallRecording.objects.get(session_id=session_id)

# 2. DB에서 고객 세그먼트 가져오기
customer_db_segments = SpeakerSegment.objects.filter(
    session_id=recording,
    speaker_label__in=['customer', 'client']
).order_by('turn_index', 'start_time')

print(f"\n1. DB 고객 세그먼트 ({customer_db_segments.count()}개):")
for idx, seg in enumerate(customer_db_segments):
    print(f"  [{idx}] turn_index={seg.turn_index}, start={seg.start_time:.2f}, text={seg.text[:50]}...")

# 3. SessionAnalysisRequest로 변환
request_data = _convert_segments_to_request(recording)

# 4. 고객 발화만 추출 (services.py와 동일한 로직)
customer_segments = []
target_speakers = ['customer', 'client']

for idx, seg_input in enumerate(request_data.segments):
    if seg_input.speaker in target_speakers:
        if seg_input.text and seg_input.text.strip():
            customer_segments.append({
                'index': idx,
                'start_time': seg_input.start_time,
                'end_time': seg_input.end_time,
                'text': seg_input.text.strip()
            })

print(f"\n2. 추출된 고객 세그먼트 ({len(customer_segments)}개):")
for idx, seg_data in enumerate(customer_segments):
    print(f"  [{idx}] start={seg_data['start_time']}, text={seg_data['text'][:50]}...")

# 5. 파이프라인 초기화 및 처리
intensity_model_path = get_intensity_model_path()
ternary_model_path = get_ternary_model_path()

pipeline = MainPipeline(
    intensity_model_path=intensity_model_path,
    ternary_model_path=ternary_model_path,
    use_two_stage_session=True
)

print(f"\n3. 파이프라인 처리 (process_single_sentence):")
pipeline_results = []
segment_map = {}

for seg_idx, seg_data in enumerate(customer_segments):
    result = pipeline.process_single_sentence(seg_data['text'], session_id)
    result_idx = len(pipeline_results)
    segment_map[result_idx] = seg_data
    pipeline_results.append(result)
    print(f"  [{seg_idx}] -> 결과[{result_idx}]: {seg_data['text'][:50]}... -> {result.label}")

print(f"\n4. 매핑 확인:")
segment_lookup = {seg.start_time: seg for seg in customer_db_segments}

for result_idx, classification_result in enumerate(pipeline_results):
    origin_info = segment_map.get(result_idx)
    if not origin_info:
        print(f"  ❌ 결과[{result_idx}]: segment_map에 없음")
        continue
    
    target_start_time = origin_info.get('start_time')
    segment = segment_lookup.get(target_start_time)
    
    if not segment:
        print(f"  ❌ 결과[{result_idx}]: start_time={target_start_time}로 DB 세그먼트를 찾을 수 없음")
        print(f"      텍스트: {origin_info['text'][:50]}...")
        print(f"      라벨: {classification_result.label}")
    else:
        # 저장된 분석 결과 확인
        try:
            analysis = CustomerAnalysisResult.objects.get(segment=segment)
            print(f"  ✅ 결과[{result_idx}] -> Segment(id={segment.id}, turn_index={segment.turn_index})")
            print(f"      텍스트: {origin_info['text'][:50]}...")
            print(f"      파이프라인 라벨: {classification_result.label}")
            print(f"      DB 저장 라벨: {analysis.label}")
            print(f"      매칭: {'✅' if classification_result.label == analysis.label else '❌ 불일치'}")
        except CustomerAnalysisResult.DoesNotExist:
            print(f"  ⚠️ 결과[{result_idx}] -> Segment(id={segment.id}): 분석 결과 없음")

print("\n" + "=" * 80)

