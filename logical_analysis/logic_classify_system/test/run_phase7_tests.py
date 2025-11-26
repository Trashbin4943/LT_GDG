"""
Phase 7 테스트 실행 스크립트
모든 단위 테스트와 통합 테스트를 실행
"""

import sys
import unittest
import io
from pathlib import Path

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_unit_tests():
    """단위 테스트 실행"""
    print("\n" + "=" * 80)
    print("Phase 7 단위 테스트 실행")
    print("=" * 80 + "\n")
    
    # 단위 테스트 디렉토리
    unit_tests_dir = Path(__file__).parent / 'unit_tests'
    
    # 테스트 로더
    loader = unittest.TestLoader()
    suite = loader.discover(str(unit_tests_dir), pattern='test_*.py')
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_integration_tests():
    """통합 테스트 실행"""
    print("\n" + "=" * 80)
    print("Phase 7 통합 테스트 실행")
    print("=" * 80 + "\n")
    
    # 통합 테스트 디렉토리
    integration_tests_dir = Path(__file__).parent / 'integration_tests'
    
    # 테스트 로더
    loader = unittest.TestLoader()
    suite = loader.discover(str(integration_tests_dir), pattern='test_*.py')
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 80)
    print("Phase 7 전체 테스트 실행")
    print("=" * 80 + "\n")
    
    # 단위 테스트 실행
    unit_result = run_unit_tests()
    
    # 통합 테스트 실행
    integration_result = run_integration_tests()
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"\n단위 테스트:")
    print(f"  - 실행: {unit_result.testsRun}")
    print(f"  - 성공: {unit_result.testsRun - len(unit_result.failures) - len(unit_result.errors)}")
    print(f"  - 실패: {len(unit_result.failures)}")
    print(f"  - 오류: {len(unit_result.errors)}")
    
    print(f"\n통합 테스트:")
    print(f"  - 실행: {integration_result.testsRun}")
    print(f"  - 성공: {integration_result.testsRun - len(integration_result.failures) - len(integration_result.errors)}")
    print(f"  - 실패: {len(integration_result.failures)}")
    print(f"  - 오류: {len(integration_result.errors)}")
    
    total_tests = unit_result.testsRun + integration_result.testsRun
    total_failures = len(unit_result.failures) + len(integration_result.failures)
    total_errors = len(unit_result.errors) + len(integration_result.errors)
    total_success = total_tests - total_failures - total_errors
    
    print(f"\n전체:")
    print(f"  - 실행: {total_tests}")
    print(f"  - 성공: {total_success}")
    print(f"  - 실패: {total_failures}")
    print(f"  - 오류: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("\n[SUCCESS] 모든 테스트 통과!")
        return 0
    else:
        print("\n[FAILED] 일부 테스트 실패")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)

