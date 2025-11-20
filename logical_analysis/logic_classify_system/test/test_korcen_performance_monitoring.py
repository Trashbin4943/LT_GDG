"""
Korcen 성능 모니터링

Korcen 필터의 처리 시간 및 성능 측정
"""
import sys
import os
import unittest
import time
import statistics
import argparse

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector


class TestKorcenPerformanceMonitoring(unittest.TestCase):
    """Korcen 성능 모니터링 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.profanity_detector = ProfanityDetector(use_korcen=True)
        
        # 테스트 케이스
        self.test_texts = [
            "시발놈아",
            "상품 문의합니다",
            "보지",
            "안녕하세요",
            "개새끼"
        ]
    
    def measure_detection_time(self, text: str, iterations: int = 100) -> list:
        """
        감지 시간 측정
        
        Args:
            text: 테스트 텍스트
            iterations: 반복 횟수
        
        Returns:
            측정된 시간 리스트 (초)
        """
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            self.profanity_detector.detect(text)
            end_time = time.perf_counter()
            
            elapsed_time = (end_time - start_time) * 1000  # ms로 변환
            times.append(elapsed_time)
        
        return times
    
    def test_single_detection_performance(self):
        """단일 감지 성능 테스트"""
        text = "시발놈아"
        iterations = 10
        
        times = self.measure_detection_time(text, iterations)
        
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n=== 단일 감지 성능 ({text}) ===")
        print(f"평균 처리 시간: {avg_time:.2f}ms")
        print(f"중앙값 처리 시간: {median_time:.2f}ms")
        print(f"최소 처리 시간: {min_time:.2f}ms")
        print(f"최대 처리 시간: {max_time:.2f}ms")
        
        # 평균 처리 시간이 합리적인 범위 내에 있는지 확인
        # (예: 100ms 이하)
        self.assertLess(avg_time, 100.0, "평균 처리 시간이 너무 깁니다")
    
    def test_multiple_texts_performance(self):
        """여러 텍스트 성능 테스트"""
        iterations = 10
        
        print("\n=== 여러 텍스트 성능 ===")
        
        for text in self.test_texts:
            times = self.measure_detection_time(text, iterations)
            avg_time = statistics.mean(times)
            
            print(f"'{text}': 평균 {avg_time:.2f}ms")
    
    def test_performance_consistency(self):
        """성능 일관성 테스트"""
        text = "시발놈아"
        iterations = 50
        
        times = self.measure_detection_time(text, iterations)
        
        std_dev = statistics.stdev(times)
        avg_time = statistics.mean(times)
        
        # 표준편차가 평균의 50% 이하인지 확인 (일관성 확인)
        coefficient_of_variation = std_dev / avg_time if avg_time > 0 else 0
        
        print(f"\n=== 성능 일관성 ===")
        print(f"평균 처리 시간: {avg_time:.2f}ms")
        print(f"표준편차: {std_dev:.2f}ms")
        print(f"변동계수: {coefficient_of_variation:.2%}")
        
        # 변동계수가 50% 이하인지 확인
        self.assertLess(coefficient_of_variation, 0.5, "성능 변동이 너무 큽니다")


def main():
    """메인 함수 (명령줄 인자 지원)"""
    parser = argparse.ArgumentParser(description="Korcen 성능 모니터링")
    parser.add_argument("--runs", type=int, default=10, help="테스트 실행 횟수")
    args = parser.parse_args()
    
    # 테스트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKorcenPerformanceMonitoring)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    import sys
    if "--runs" in sys.argv or len(sys.argv) > 1:
        main()
    else:
        unittest.main()
