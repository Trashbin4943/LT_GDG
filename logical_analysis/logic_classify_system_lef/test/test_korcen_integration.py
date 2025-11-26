"""
Korcen 필터 통합 테스트 스크립트

이 테스트는 Korcen 필터가 ProfanityDetector에 올바르게 통합되었는지 확인합니다.

주요 검증 항목:
1. Korcen 필터 단독 동작 검증
2. ProfanityDetector 통합 검증
3. 엣지 케이스 처리 검증

실행 방법:
    방법 1 (권장): 프로젝트 루트에서 실행
        python -m linguaproject.logic_classify_system.test.test_korcen_integration
    
    방법 2: 직접 실행 (프로젝트 루트에서)
        python linguaproject/logic_classify_system/test/test_korcen_integration.py
    
    방법 3: pytest 사용
        pytest linguaproject/logic_classify_system/test/test_korcen_integration.py -v

상세 문서: test/README_TEST_KORCEN.md
"""

import sys
import io
from pathlib import Path

# Windows 콘솔 인코딩 문제 해결
if sys.platform == "win32":
    try:
        # UTF-8 출력 설정 (Python 3.7+)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        else:
            # Python 3.6 이하 호환
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        # 실패 시 기본 인코딩 유지
        pass

# 프로젝트 루트를 경로에 추가 (단독 실행 시)
if __name__ == "__main__":
    # 현재 파일의 위치에서 프로젝트 루트 찾기
    # test_korcen_integration.py -> test/ -> logic_classify_system/ -> linguaproject/ -> LT_GDG/
    current_file = Path(__file__).resolve()
    # test/ 디렉토리에서 시작하여 LT_GDG/까지 올라가기
    project_root = current_file.parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from linguaproject.logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
from linguaproject.logic_classify_system.profanity_filter.korcen_filter import KorcenFilter

def test_korcen_filter():
    """Korcen 필터 단독 테스트"""
    print("=" * 60)
    print("1. Korcen 필터 단독 테스트")
    print("=" * 60)
    
    korcen = KorcenFilter()
    
    test_cases = [
        ("시발놈아", True, "PROFANITY"),
        ("보지 보여줘", True, "SEXUAL_HARASSMENT"),
        ("틀딱년 나가", True, "INSULT"),
        ("깜둥이 꺼져", True, "HATE_SPEECH"),
        ("안녕하세요", False, None),
        ("죽여버리겠다", True, "VIOLENCE_THREAT"),  # Baseline 규칙
        ("다시 방문해주세요", False, None),  # False Positive
        ("개발자입니다", False, None),  # False Positive
    ]
    
    for text, expected_prof, expected_cat in test_cases:
        is_prof, category, confidence = korcen.check_profanity(text)
        status = "[PASS]" if (is_prof == expected_prof and category == expected_cat) else "[FAIL]"
        print(f"{status} '{text}'")
        print(f"   -> is_profanity: {is_prof} (예상: {expected_prof})")
        print(f"   -> category: {category} (예상: {expected_cat})")
        print(f"   -> confidence: {confidence:.2f}")
        print()

def test_profanity_detector_with_korcen():
    """ProfanityDetector with Korcen 테스트"""
    print("=" * 60)
    print("2. ProfanityDetector (Korcen 사용) 테스트")
    print("=" * 60)
    
    detector = ProfanityDetector(use_korcen=True)
    
    test_cases = [
        "시발놈아",
        "보지 보여줘",
        "틀딱년 나가",
        "깜둥이 꺼져",
        "안녕하세요",
        "죽여버리겠다",  # Baseline 규칙 (위협 표현)
        "다시 방문해주세요",  # False Positive
        "개발자입니다",  # False Positive
    ]
    
    for text in test_cases:
        result = detector.detect(text)
        print(f"'{text}'")
        print(f"   -> is_profanity: {result.is_profanity}")
        print(f"   -> category: {result.category}")
        print(f"   -> confidence: {result.confidence:.2f}")
        print(f"   -> method: {result.method}")
        print()

def test_profanity_detector_baseline_only():
    """ProfanityDetector (Baseline만 사용) 테스트"""
    print("=" * 60)
    print("3. ProfanityDetector (Baseline만 사용) 테스트")
    print("=" * 60)
    
    detector = ProfanityDetector(use_korcen=False)
    
    test_cases = [
        "시발놈아",
        "죽여버리겠다",  # Baseline 규칙 (위협 표현)
        "안녕하세요",
    ]
    
    for text in test_cases:
        result = detector.detect(text)
        print(f"'{text}'")
        print(f"   -> is_profanity: {result.is_profanity}")
        print(f"   -> category: {result.category}")
        print(f"   -> confidence: {result.confidence:.2f}")
        print(f"   -> method: {result.method}")
        print()

def test_edge_cases():
    """엣지 케이스 테스트"""
    print("=" * 60)
    print("4. 엣지 케이스 테스트")
    print("=" * 60)
    
    detector = ProfanityDetector(use_korcen=True)
    
    edge_cases = [
        # 기본 엣지 케이스
        ("", "빈 문자열"),
        ("   ", "공백만"),
        ("시발", "짧은 욕설"),
        ("시발 시발 시발", "반복 욕설"),
        ("안녕하세요. 시발놈아. 감사합니다.", "문장 중간 욕설"),
        ("시발놈아 보지 보여줘", "다중 카테고리"),
        
        # 특수 문자 및 변형
        ("시발놈아!!!", "특수문자 포함"),
        ("시발놈아???", "물음표 포함"),
        ("시발놈아...", "말줄임표 포함"),
        ("시발놈아123", "숫자 포함"),
        ("시발놈아@#$", "기호 포함"),
        
        # 공백 변형
        ("시발\n놈아", "개행 문자 포함"),
        ("시발\t놈아", "탭 문자 포함"),
        ("시발  놈아", "연속 공백"),
        
        # 매우 긴 문자열
        ("안녕하세요. " * 50 + "시발놈아", "매우 긴 문자열"),
        ("시발놈아 " * 100, "반복된 욕설 (매우 긴)"),
        
        # 혼합 케이스
        ("안녕하세요 시발놈아 감사합니다", "정상 문장과 욕설 혼합"),
        ("시발놈아 안녕하세요", "욕설 후 정상 문장"),
        ("시발놈아! 안녕하세요?", "구두점 혼합"),
        
        # 경계 케이스
        ("시", "한 글자"),
        ("시발놈", "부분 일치"),
        ("놈아", "부분 일치"),
    ]
    
    for text, description in edge_cases:
        result = detector.detect(text)
        # 빈 문자열이나 특수 문자는 repr로 표시
        display_text = repr(text) if not text or any(c in text for c in ['\n', '\t', '\r']) else f"'{text}'"
        print(f"{display_text} ({description})")
        print(f"   -> is_profanity: {result.is_profanity}")
        print(f"   -> category: {result.category}")
        print(f"   -> confidence: {result.confidence:.2f}")
        print(f"   -> method: {result.method}")
        print()

if __name__ == "__main__":
    import argparse
    
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='Korcen 필터 통합 테스트')
    parser.add_argument('--output', '-o', type=str, help='출력 파일 경로 (선택사항)')
    parser.add_argument('--test', '-t', type=str, choices=['all', 'korcen', 'detector', 'baseline', 'edge'], 
                       default='all', help='실행할 테스트 선택')
    args = parser.parse_args()
    
    # 출력 리다이렉션 (선택사항)
    original_stdout = sys.stdout
    if args.output:
        try:
            sys.stdout = open(args.output, 'w', encoding='utf-8')
            print(f"출력을 파일로 저장합니다: {args.output}\n")
        except Exception as e:
            print(f"파일 출력 실패: {e}", file=sys.stderr)
            sys.stdout = original_stdout
    
    try:
        print("\n" + "=" * 60)
        print("Korcen 필터 통합 테스트 시작")
        print("=" * 60 + "\n")
        
        # 테스트 실행
        if args.test in ['all', 'korcen']:
            test_korcen_filter()
        
        if args.test in ['all', 'detector']:
            test_profanity_detector_with_korcen()
        
        if args.test in ['all', 'baseline']:
            test_profanity_detector_baseline_only()
        
        if args.test in ['all', 'edge']:
            test_edge_cases()
        
        print("=" * 60)
        print("[SUCCESS] 모든 테스트 완료")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 출력 복원
        if args.output and sys.stdout != original_stdout:
            sys.stdout.close()
            sys.stdout = original_stdout
            print(f"\n테스트 결과가 저장되었습니다: {args.output}")

