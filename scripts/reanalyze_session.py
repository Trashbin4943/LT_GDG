"""
특정 세션을 다시 분석하는 스크립트
"""

import os
import sys
from pathlib import Path

# Django 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from audio_process.models import CallRecording
from logical_analysis.services import analyze_from_db_segments


def reanalyze_session(session_id: str):
    """세션을 다시 분석"""
    print(f"세션 재분석 시작: {session_id}")
    
    try:
        recording = CallRecording.objects.get(session_id=session_id)
        print(f"✅ CallRecording 찾음: {recording.file_name}")
        
        # 기존 분석 결과 삭제 (선택사항)
        from logical_analysis.models import CustomerAnalysisResult
        deleted_count = CustomerAnalysisResult.objects.filter(
            segment__session_id=recording
        ).delete()[0]
        print(f"🗑️ 기존 분석 결과 삭제: {deleted_count}개")
        
        # 재분석 실행
        result = analyze_from_db_segments(
            recording,
            auto_generate_solution=False,
            skip_existing=False
        )
        
        print(f"\n✅ 재분석 완료!")
        print(f"   처리된 발화: {result.get('processed_customer_turns', 0)}")
        print(f"   에러 발생: {result.get('error_turns', 0)}")
        
        # 결과 확인
        analysis_results = CustomerAnalysisResult.objects.filter(
            segment__session_id=recording
        ).select_related('segment')
        
        print(f"\n📊 분석 결과 요약:")
        print(f"   총 결과 수: {analysis_results.count()}")
        
        profanity_results = analysis_results.filter(is_profanity=True)
        print(f"   욕설 감지: {profanity_results.count()}개")
        
        if profanity_results.exists():
            print(f"\n   ⚠️ 욕설 감지된 발화:")
            for res in profanity_results:
                print(f"      - {res.segment.text[:60]}...")
                print(f"        위험도: {res.score_risk:.2f}, 욕설 점수: {res.score_profanity:.2f}")
        
        # '시발' 포함 발화 확인
        from audio_process.models import SpeakerSegment
        segments_with_profanity = SpeakerSegment.objects.filter(
            session_id=recording,
            text__icontains='시발'
        )
        if segments_with_profanity.exists():
            print(f"\n   🔍 '시발' 포함 발화:")
            for seg in segments_with_profanity:
                try:
                    analysis = CustomerAnalysisResult.objects.get(segment=seg)
                    print(f"      - {seg.text[:60]}...")
                    print(f"        욕설: {analysis.is_profanity}, 점수: {analysis.score_profanity:.2f}")
                except CustomerAnalysisResult.DoesNotExist:
                    print(f"      - {seg.text[:60]}... (분석 결과 없음)")
        
    except CallRecording.DoesNotExist:
        print(f"❌ 세션을 찾을 수 없습니다: {session_id}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='세션 재분석')
    parser.add_argument('session_id', help='재분석할 세션 ID')
    
    args = parser.parse_args()
    reanalyze_session(args.session_id)

