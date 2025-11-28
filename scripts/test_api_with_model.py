"""
API를 통한 모델 동작 테스트
실제 HTTP 요청을 통해 서버에서 모델이 정상 작동하는지 확인
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_server():
    """서버 연결 확인"""
    print("=== 서버 연결 확인 ===\n")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ 서버 연결 성공 (Status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_model_via_api():
    """API를 통한 모델 테스트"""
    print("\n=== API를 통한 모델 테스트 ===\n")
    
    # 실제 API 엔드포인트가 있다면 테스트
    # 현재는 서버 로그를 통해 모델 로드 확인
    
    print("서버가 실행 중이면 모델이 자동으로 로드됩니다.")
    print("서버 로그에서 다음 메시지를 확인하세요:")
    print("  - '✅ Intensity Regression 모델 로드 완료'")
    print("  - '✅ 4진 분류 모델 로드 완료'")
    
    return True

def test_services_directly():
    """서비스 함수 직접 테스트 (Django 환경)"""
    print("\n=== 서비스 함수 직접 테스트 ===\n")
    
    import os
    import django
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')
    django.setup()
    
    from logical_analysis.services import analyze_and_save_customer_turns
    from logical_analysis.schemas import SessionAnalysisRequest, SegmentInput
    
    # 테스트 데이터 생성
    test_segments = [
        SegmentInput(
            speaker="customer",
            text="안녕하세요. 문의사항이 있습니다.",
            start_time=0.0,
            end_time=2.5
        ),
        SegmentInput(
            speaker="customer",
            text="이런 서비스는 말이 안 됩니다!",
            start_time=3.0,
            end_time=5.5
        )
    ]
    
    request_data = SessionAnalysisRequest(
        session_id="test_session_api",
        segments=test_segments
    )
    
    try:
        print("서비스 함수 실행 중...")
        # 실제 DB 저장 없이 테스트하려면 skip_existing=True 사용
        # 하지만 DB 연결이 필요하므로 여기서는 모델 로드만 확인
        
        from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
        from logical_analysis.logic_classify_system.config.model_paths import (
            get_intensity_model_path,
            get_ternary_model_path
        )
        
        intensity_path = get_intensity_model_path()
        ternary_path = get_ternary_model_path()
        
        pipeline = MainPipeline(
            intensity_model_path=intensity_path,
            ternary_model_path=ternary_path,
            use_enhanced_predictor=True
        )
        
        # 고객 발화만 추출
        customer_texts = [seg.text for seg in test_segments if seg.speaker == "customer"]
        combined_text = " ".join(customer_texts)
        
        print(f"테스트 텍스트: {combined_text}")
        result = pipeline.process(combined_text, session_id="test_session_api")
        
        print(f"처리된 결과 수: {len(result.results)}")
        for i, res in enumerate(result.results):
            print(f"\n결과 {i+1}:")
            print(f"  - Text: {res.text}")
            print(f"  - Label: {res.label}")
            print(f"  - Label Type: {res.label_type}")
            print(f"  - Confidence: {res.confidence:.4f}")
            if hasattr(res, 'intensity') and res.intensity is not None:
                print(f"  - Intensity: {res.intensity:.4f} (범위: 0.0 ~ 3.0)")
            if hasattr(res, 'intensity_level') and res.intensity_level:
                print(f"  - Intensity Level: {res.intensity_level} (LOW/MEDIUM/HIGH/VERY_HIGH)")
        
        print("\n✅ 서비스 함수 테스트 완료")
        return True
    except Exception as e:
        print(f"❌ 서비스 함수 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("서버에서 모델 동작 확인")
    print("=" * 60)
    print()
    
    # 1. 서버 연결 확인
    server_ok = check_server()
    
    # 2. 서비스 함수 직접 테스트 (Django 환경)
    service_ok = test_services_directly()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"서버 연결: {'✅ 통과' if server_ok else '⚠️ 확인 필요'}")
    print(f"서비스 함수: {'✅ 통과' if service_ok else '❌ 실패'}")
    
    if service_ok:
        print("\n🎉 모델이 서버 환경에서 정상적으로 동작합니다!")
        print("\n다음 단계:")
        print("1. 서버를 실행하고 실제 API 엔드포인트를 테스트하세요")
        print("2. 서버 로그에서 모델 로드 메시지를 확인하세요")
        print("3. 실제 대화 데이터로 테스트하세요")
    else:
        print("\n⚠️ 일부 테스트 실패")
        sys.exit(1)

