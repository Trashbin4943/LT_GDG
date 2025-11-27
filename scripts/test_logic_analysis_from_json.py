"""
JSON 파일을 사용한 논리분석 테스트 스크립트

사용법:
    python scripts/test_logic_analysis_from_json.py <json_file_path> [--session-id SESSION_ID]

예시:
    python scripts/test_logic_analysis_from_json.py segments_example.json
    python scripts/test_logic_analysis_from_json.py segments_example.json --session-id test-session-001
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# requests는 API 호출 시에만 필요
try:
    import requests
except ImportError:
    requests = None

# Django 설정 로드
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')

import django
django.setup()

from accounts.models import User
from rest_framework_simplejwt.tokens import AccessToken
from audio_process.models import CallRecording, SpeakerSegment
from logical_analysis.services import analyze_and_save_customer_turns
from logical_analysis.schemas import SessionAnalysisRequest, SegmentInput
from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)
from logical_analysis.logic_classify_system.models import AIHUB_MODEL_DIR


def load_json_file(json_path: str) -> List[Dict[str, Any]]:
    """
    JSON 파일을 로드합니다.
    
    Args:
        json_path: JSON 파일 경로
        
    Returns:
        세그먼트 리스트
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError(f"JSON 파일은 리스트 형식이어야 합니다. 현재 형식: {type(data)}")
    
    print(f"✅ JSON 파일에서 {len(data)}개의 세그먼트를 로드했습니다.")
    return data


def convert_json_to_session_request(
    segments: List[Dict[str, Any]], 
    session_id: str
) -> SessionAnalysisRequest:
    """
    JSON 세그먼트 데이터를 SessionAnalysisRequest로 변환합니다.
    
    Args:
        segments: JSON 세그먼트 리스트 (start, end, text, speaker 포함)
        session_id: 세션 ID
        
    Returns:
        SessionAnalysisRequest 객체
    """
    segment_inputs = []
    
    for idx, seg in enumerate(segments):
        # 필수 필드 확인
        if 'text' not in seg or 'speaker' not in seg:
            print(f"⚠️ 경고: 인덱스 {idx}의 세그먼트에 필수 필드가 없습니다. 건너뜁니다.")
            continue
        
        # speaker 값을 통일된 형식으로 변환
        speaker = seg['speaker'].lower()
        if speaker in ['client', 'customer']:
            speaker = 'customer'
        elif speaker in ['counselor', 'agent', 'counselor']:
            speaker = 'agent'
        else:
            print(f"⚠️ 경고: 인덱스 {idx}의 speaker 값이 예상과 다릅니다: {speaker}. 'customer'로 설정합니다.")
            speaker = 'customer'  # 기본값
        
        segment_inputs.append(SegmentInput(
            speaker=speaker,
            text=str(seg['text']).strip(),
            start_time=float(seg.get('start', 0.0)) if seg.get('start') is not None else None,
            end_time=float(seg.get('end', 0.0)) if seg.get('end') is not None else None,
            timestamp=None
        ))
    
    print(f"✅ {len(segment_inputs)}개의 세그먼트를 SessionAnalysisRequest로 변환했습니다.")
    return SessionAnalysisRequest(
        session_id=session_id,
        segments=segment_inputs
    )


def create_test_recording(session_id: str, user: User, segments: List[Dict[str, Any]]) -> CallRecording:
    """
    테스트용 CallRecording과 SpeakerSegment를 생성합니다.
    
    Args:
        session_id: 세션 ID
        user: 사용자 객체
        segments: 세그먼트 리스트
        
    Returns:
        CallRecording 객체
    """
    # CallRecording 생성 또는 가져오기
    recording, created = CallRecording.objects.get_or_create(
        session_id=session_id,
        defaults={
            'file_name': f'test_{session_id}.json',
            'uploader': user,
            'processed': False
        }
    )
    
    if created:
        print(f"✅ 새로운 CallRecording 생성: {session_id}")
    else:
        print(f"ℹ️ 기존 CallRecording 사용: {session_id}")
        # 기존 세그먼트 삭제 (테스트를 위해)
        recording.segments.all().delete()
        print(f"  기존 세그먼트 삭제 완료")
    
    # SpeakerSegment 생성
    segment_objects = []
    for idx, seg in enumerate(segments):
        speaker_label = seg.get('speaker', 'unknown').lower()
        if speaker_label in ['client', 'customer']:
            speaker_label = 'client'
        elif speaker_label in ['counselor', 'agent']:
            speaker_label = 'counselor'
        else:
            speaker_label = 'unknown'
        
        segment_objects.append(SpeakerSegment(
            session_id=recording,
            turn_index=idx,
            speaker_label=speaker_label,
            start_time=float(seg.get('start', 0.0)),
            end_time=float(seg.get('end', 0.0)),
            text=str(seg.get('text', '')).strip(),
            is_counselor=(speaker_label == 'counselor')
        ))
    
    SpeakerSegment.objects.bulk_create(segment_objects)
    print(f"✅ {len(segment_objects)}개의 SpeakerSegment 생성 완료")
    
    # CallRecording 업데이트
    recording.processed = True
    if segments:
        recording.duration = float(segments[-1].get('end', 0.0))
    recording.save()
    
    return recording


def test_logic_analysis_via_api(
    json_path: str,
    session_id: str = None,
    base_url: str = "http://127.0.0.1:8000",
    username: str = "admin"
):
    """
    API를 통해 논리분석을 테스트합니다.
    
    Args:
        json_path: JSON 파일 경로
        session_id: 세션 ID (없으면 파일명 기반으로 생성)
        base_url: API 기본 URL
        username: 로그인할 사용자명
    """
    if requests is None:
        print("❌ requests 모듈이 설치되지 않았습니다. pip install requests를 실행하세요.")
        return
    # 1. JSON 파일 로드
    segments = load_json_file(json_path)
    
    # 2. Session ID 생성
    if not session_id:
        session_id = f"test-{Path(json_path).stem}-{hash(json_path) % 10000}"
    
    print(f"\n📋 세션 ID: {session_id}")
    
    # 3. SessionAnalysisRequest 변환
    request_data = convert_json_to_session_request(segments, session_id)
    
    # 4. JWT 토큰 획득
    try:
        user = User.objects.get(username=username)
        token = AccessToken.for_user(user)
        print(f"✅ JWT 토큰 생성 완료 (사용자: {username})")
    except User.DoesNotExist:
        print(f"❌ 사용자를 찾을 수 없습니다: {username}")
        print("   먼저 사용자를 생성하거나 다른 사용자명을 사용하세요.")
        return
    
    # 5. API 호출
    url = f"{base_url}/api/logic/analyze/customer"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # SessionAnalysisRequest를 딕셔너리로 변환
    payload = {
        "session_id": request_data.session_id,
        "segments": [
            {
                "speaker": seg.speaker,
                "text": seg.text,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "timestamp": seg.timestamp
            }
            for seg in request_data.segments
        ]
    }
    
    params = {
        "auto_generate_solution": False,  # 테스트에서는 솔루션 생성 생략
        "skip_existing": False
    }
    
    print(f"\n🚀 API 호출 시작...")
    print(f"   URL: {url}")
    print(f"   세그먼트 수: {len(payload['segments'])}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, params=params, timeout=300)
        
        print(f"\n📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 분석 성공!")
            print(f"\n📈 분석 결과:")
            print(f"   - 처리된 고객 발화: {result.get('processed_customer_turns', 0)}")
            print(f"   - 스킵된 발화: {result.get('skipped_turns', 0)}")
            print(f"   - 에러 발생: {result.get('error_turns', 0)}")
            print(f"   - 생성된 솔루션: {result.get('generated_solutions', 0)}")
            
            # 결과 조회
            get_url = f"{base_url}/api/logic/{session_id}"
            get_response = requests.get(get_url)
            
            if get_response.status_code == 200:
                analysis_result = get_response.json()
                print(f"\n📋 상세 분석 결과:")
                print(f"   - 총 문장 수: {analysis_result.get('summary', {}).get('total_sentences', 0)}")
                print(f"   - 위험 문장 수: {analysis_result.get('summary', {}).get('risk_count', 0)}")
                print(f"   - 최고 위험도: {analysis_result.get('summary', {}).get('highest_risk_score', 'N/A')}")
                print(f"   - 주요 라벨: {analysis_result.get('summary', {}).get('primary_label', 'N/A')}")
                
                # 위험도가 높은 문장 출력
                results = analysis_result.get('results', [])
                high_risk_results = [r for r in results if r.get('score_risk', 0) >= 0.6]
                if high_risk_results:
                    print(f"\n⚠️ 위험도 높은 문장 ({len(high_risk_results)}개):")
                    for r in high_risk_results[:5]:  # 최대 5개만 출력
                        print(f"   - [{r.get('label', 'N/A')}] {r.get('text', '')[:50]}...")
                        print(f"     위험도: {r.get('score_risk', 0):.2f}, 욕설: {r.get('is_profanity', False)}")
        else:
            print(f"❌ 분석 실패!")
            print(f"   응답: {response.text}")
            try:
                error_data = response.json()
                print(f"   에러 메시지: {error_data.get('message', 'N/A')}")
            except:
                pass
                
    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 실패: {e}")
        print(f"   서버가 실행 중인지 확인하세요: {base_url}")


def test_logic_analysis_direct(
    json_path: str,
    session_id: str = None,
    username: str = "admin"
):
    """
    직접 서비스 함수를 호출하여 논리분석을 테스트합니다.
    (DB에 CallRecording과 SpeakerSegment가 필요함)
    
    Args:
        json_path: JSON 파일 경로
        session_id: 세션 ID (없으면 파일명 기반으로 생성)
        username: 사용자명
    """
    # 1. JSON 파일 로드
    segments = load_json_file(json_path)
    
    # 2. Session ID 생성
    if not session_id:
        session_id = f"test-{Path(json_path).stem}-{hash(json_path) % 10000}"
    
    print(f"\n📋 세션 ID: {session_id}")
    
    # 3. 사용자 조회
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ 사용자를 찾을 수 없습니다: {username}")
        return
    
    # 4. CallRecording 및 SpeakerSegment 생성
    recording = create_test_recording(session_id, user, segments)
    
    # 5. SessionAnalysisRequest 변환
    request_data = convert_json_to_session_request(segments, session_id)
    
    # 6. AI Hub 모델 경로 확인 및 출력
    import os
    from pathlib import Path
    
    aihub_base_path = os.getenv('AIHUB_BASE_MODEL_PATH') or str(AIHUB_MODEL_DIR)
    aihub_model1_checkpoint = os.getenv('AIHUB_MODEL1_CHECKPOINT')
    aihub_model2_checkpoint = os.getenv('AIHUB_MODEL2_CHECKPOINT')
    
    print(f"\n📁 AI Hub 모델 경로 설정:")
    print(f"   base_path: {aihub_base_path}")
    print(f"   존재 여부: {Path(aihub_base_path).exists() if aihub_base_path else False}")
    print(f"   model1_checkpoint: {aihub_model1_checkpoint}")
    print(f"   model2_checkpoint: {aihub_model2_checkpoint}")
    
    # 파이프라인 초기화 테스트 (AI Hub 모델 로드 상태 확인)
    try:
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        test_pipeline = MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_two_stage_session=True,
            aihub_base_path=aihub_base_path if Path(aihub_base_path).exists() else None,
            aihub_model1_checkpoint=aihub_model1_checkpoint,
            aihub_model2_checkpoint=aihub_model2_checkpoint
        )
        
        # AI Hub 모델 로드 상태 확인
        if hasattr(test_pipeline, 'baseline_session') and test_pipeline.baseline_session:
            aihub_status = test_pipeline.baseline_session.get_session_info().get('has_aihub_model', False)
            print(f"🤖 AI Hub 모델 로드 상태: {'✅ 로드됨' if aihub_status else '❌ 로드 안 됨'}")
        else:
            print(f"⚠️ BaselineSession이 초기화되지 않았습니다.")
    except Exception as e:
        print(f"⚠️ 파이프라인 초기화 테스트 실패: {e}")
    
    # 7. 논리분석 실행
    print(f"\n🚀 논리분석 시작...")
    try:
        result = analyze_and_save_customer_turns(
            request_data,
            auto_generate_solution=False,  # 테스트에서는 솔루션 생성 생략
            skip_existing=False
        )
        
        print(f"\n✅ 분석 완료!")
        print(f"\n📈 분석 결과:")
        print(f"   - 처리된 고객 발화: {result.get('processed_customer_turns', 0)}")
        print(f"   - 스킵된 발화: {result.get('skipped_turns', 0)}")
        print(f"   - 에러 발생: {result.get('error_turns', 0)}")
        print(f"   - 생성된 솔루션: {result.get('generated_solutions', 0)}")
        
        # DB에서 결과 조회
        from logical_analysis.models import CustomerAnalysisResult
        analysis_results = CustomerAnalysisResult.objects.filter(
            segment__session_id=recording
        ).select_related('segment')
        
        print(f"\n📋 상세 분석 결과 ({analysis_results.count()}개):")
        for res in analysis_results[:10]:  # 최대 10개만 출력
            print(f"   - [{res.label}] {res.segment.text[:50]}...")
            print(f"     위험도: {res.score_risk:.2f}, 욕설: {res.is_profanity}, 신뢰도: {res.classification_confidence:.2f}")
            
            # AI Hub 모델 사용 여부 확인 (feature_scores_extra에서)
            if hasattr(res, 'feature_scores_extra') and res.feature_scores_extra:
                intensity = res.feature_scores_extra.get('intensity')
                intensity_level = res.feature_scores_extra.get('intensity_level')
                is_immoral = res.feature_scores_extra.get('is_immoral')
                if is_immoral is not None or intensity is not None:
                    print(f"     🤖 AI Hub 모델 결과:")
                    if is_immoral is not None:
                        print(f"        - is_immoral: {is_immoral}")
                    if intensity is not None:
                        print(f"        - intensity: {intensity}, level: {intensity_level}")
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description='JSON 파일을 사용한 논리분석 테스트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # API를 통해 테스트
  python scripts/test_logic_analysis_from_json.py segments_example.json --method api
  
  # 직접 서비스 함수 호출로 테스트
  python scripts/test_logic_analysis_from_json.py segments_example.json --method direct
  
  # 세션 ID 지정
  python scripts/test_logic_analysis_from_json.py segments_example.json --session-id my-test-session
        """
    )
    
    parser.add_argument('json_file', help='JSON 파일 경로')
    parser.add_argument('--session-id', help='세션 ID (기본값: 파일명 기반 자동 생성)')
    parser.add_argument('--method', choices=['api', 'direct'], default='direct',
                       help='테스트 방법: api (HTTP API 호출) 또는 direct (직접 함수 호출)')
    parser.add_argument('--base-url', default='http://127.0.0.1:8000',
                       help='API 기본 URL (기본값: http://127.0.0.1:8000)')
    parser.add_argument('--username', default='admin',
                       help='사용자명 (기본값: admin)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("논리분석 JSON 테스트 스크립트")
    print("=" * 60)
    print(f"JSON 파일: {args.json_file}")
    print(f"테스트 방법: {args.method}")
    print("=" * 60)
    
    if args.method == 'api':
        test_logic_analysis_via_api(
            args.json_file,
            args.session_id,
            args.base_url,
            args.username
        )
    else:
        test_logic_analysis_direct(
            args.json_file,
            args.session_id,
            args.username
        )
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == '__main__':
    main()

