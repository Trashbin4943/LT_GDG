"""
DB에서 Intensity 정보 확인
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from logical_analysis.models import CustomerAnalysisResult
from audio_process.models import CallRecording, SpeakerSegment

session_id = "a21cbea6-59ae-400e-bb4d-e75b0e18d9ed"

recording = CallRecording.objects.get(session_id=session_id)
results = CustomerAnalysisResult.objects.filter(
    segment__session_id=recording
).select_related('segment').order_by('segment__start_time')

print(f"세션 ID: {session_id}")
print(f"분석 결과 수: {results.count()}\n")

for res in results:
    print(f"텍스트: {res.segment.text[:60]}...")
    print(f"  라벨: {res.label}, 타입: {res.label_type}")
    print(f"  위험도: {res.score_risk:.2f}, 욕설 점수: {res.score_profanity:.2f}")
    
    # Intensity 정보 확인
    if res.feature_scores_extra:
        intensity = res.feature_scores_extra.get('intensity')
        intensity_level = res.feature_scores_extra.get('intensity_level')
        print(f"  Intensity: {intensity}, Level: {intensity_level}")
    else:
        print(f"  Intensity: None (feature_scores_extra 없음)")
    
    print()

