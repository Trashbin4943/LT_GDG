"""
세그먼트 매핑 문제 진단 스크립트
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
from logical_analysis.schemas import SessionAnalysisRequest

session_id = "a21cbea6-59ae-400e-bb4d-e75b0e18d9ed"

print("=" * 80)
print("세그먼트 매핑 문제 진단")
print("=" * 80)

# 1. CallRecording 조회
recording = CallRecording.objects.get(session_id=session_id)

# 2. DB에서 모든 세그먼트 가져오기
all_db_segments = SpeakerSegment.objects.filter(
    session_id=recording
).order_by('turn_index', 'start_time')

print(f"\n1. DB의 모든 세그먼트 ({all_db_segments.count()}개):")
for idx, seg in enumerate(all_db_segments):
    print(f"  [{idx}] turn_index={seg.turn_index}, speaker={seg.speaker_label}, "
          f"start={seg.start_time:.2f}, text={seg.text[:40]}...")

# 3. 고객 세그먼트만 가져오기
customer_db_segments = SpeakerSegment.objects.filter(
    session_id=recording,
    speaker_label__in=['customer', 'client']
).order_by('turn_index', 'start_time')

print(f"\n2. DB의 고객 세그먼트만 ({customer_db_segments.count()}개):")
for idx, seg in enumerate(customer_db_segments):
    print(f"  [{idx}] turn_index={seg.turn_index}, speaker={seg.speaker_label}, "
          f"start={seg.start_time:.2f}, text={seg.text[:40]}...")

# 4. SessionAnalysisRequest로 변환
request_data = _convert_segments_to_request(recording)

print(f"\n3. SessionAnalysisRequest의 모든 세그먼트 ({len(request_data.segments)}개):")
for idx, seg in enumerate(request_data.segments):
    print(f"  [{idx}] speaker={seg.speaker}, start={seg.start_time}, text={seg.text[:40]}...")

# 5. 고객 발화만 추출 (services.py와 동일한 로직)
customer_segments = []
target_speakers = ['customer', 'client']

for idx, seg_input in enumerate(request_data.segments):
    if seg_input.speaker in target_speakers:
        if seg_input.text and seg_input.text.strip():
            customer_segments.append({
                'index': idx,  # 원본 request_data.segments의 인덱스
                'start_time': seg_input.start_time,
                'end_time': seg_input.end_time,
                'text': seg_input.text.strip()
            })

print(f"\n4. 추출된 고객 세그먼트 ({len(customer_segments)}개):")
for idx, seg_data in enumerate(customer_segments):
    print(f"  [{idx}] 원본인덱스={seg_data['index']}, start={seg_data['start_time']}, "
          f"text={seg_data['text'][:40]}...")

# 6. segment_lookup 생성 (services.py와 동일)
segment_lookup = {seg.start_time: seg for seg in customer_db_segments}

print(f"\n5. segment_lookup (start_time -> DB Segment):")
for start_time, seg in sorted(segment_lookup.items()):
    print(f"  start_time={start_time:.2f} -> Segment(id={seg.id}, turn_index={seg.turn_index}, text={seg.text[:40]}...)")

# 7. 매핑 테스트
print(f"\n6. 매핑 테스트:")
print(f"  customer_segments 수: {len(customer_segments)}")
print(f"  customer_db_segments 수: {len(customer_db_segments)}")
print(f"  segment_lookup 키 수: {len(segment_lookup)}")

mapping_issues = []
for seg_idx, seg_data in enumerate(customer_segments):
    target_start_time = seg_data.get('start_time')
    segment = segment_lookup.get(target_start_time)
    
    if not segment:
        mapping_issues.append({
            'seg_idx': seg_idx,
            'start_time': target_start_time,
            'text': seg_data['text'][:50],
            'issue': 'start_time으로 매핑 실패'
        })
        print(f"  ❌ [{seg_idx}] start_time={target_start_time} 매핑 실패: {seg_data['text'][:40]}...")
    else:
        print(f"  ✅ [{seg_idx}] start_time={target_start_time:.2f} -> Segment(id={segment.id}, turn_index={segment.turn_index})")

# 8. 분석 결과와 비교
print(f"\n7. 저장된 분석 결과와 비교:")
analysis_results = CustomerAnalysisResult.objects.filter(
    segment__session_id=recording
).select_related('segment').order_by('segment__start_time')

for idx, res in enumerate(analysis_results):
    print(f"  [{idx}] Segment(id={res.segment.id}, turn_index={res.segment.turn_index}, "
          f"start={res.segment.start_time:.2f})")
    print(f"      텍스트: {res.segment.text[:50]}...")
    print(f"      라벨: {res.label}, 위험도: {res.score_risk:.2f}")

# 9. 매핑 문제 요약
if mapping_issues:
    print(f"\n⚠️ 매핑 문제 발견: {len(mapping_issues)}개")
    for issue in mapping_issues:
        print(f"  - 세그먼트 {issue['seg_idx']}: {issue['issue']}")
        print(f"    텍스트: {issue['text']}")
        print(f"    start_time: {issue['start_time']}")
else:
    print(f"\n✅ 매핑 문제 없음")

# 10. start_time 정확도 확인
print(f"\n8. start_time 정확도 확인:")
for seg_idx, seg_data in enumerate(customer_segments):
    target_start_time = seg_data.get('start_time')
    # 가장 가까운 start_time 찾기
    closest_seg = None
    min_diff = float('inf')
    for seg in customer_db_segments:
        diff = abs(seg.start_time - target_start_time) if target_start_time else float('inf')
        if diff < min_diff:
            min_diff = diff
            closest_seg = seg
    
    if min_diff > 0.01:  # 0.01초 이상 차이
        print(f"  ⚠️ [{seg_idx}] start_time 불일치: 요청={target_start_time}, "
              f"DB={closest_seg.start_time if closest_seg else None}, 차이={min_diff:.3f}초")

print("\n" + "=" * 80)

