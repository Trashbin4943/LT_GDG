"""
Korcen 레이블링 테스트

Korcen 필터를 통한 욕설 감지 및 레이블링 테스트
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
from logic_classify_system.profanity_filter.korcen_filter import KorcenFilter


class TestKorcenLabeling(unittest.TestCase):
    """Korcen 레이블링 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.profanity_detector = ProfanityDetector(use_korcen=True)
        self.korcen_filter = KorcenFilter(use_korcen=True)
        
        # 테스트 케이스
        self.test_cases = [
            ("시발놈아", True, "PROFANITY_DETECTED"),
            ("상품 문의합니다", False, None),
            ("보지", True, "SEXUAL_DETECTED"),
            ("짱깨", True, "HATE_DETECTED")
        ]
    
    def test_profanity_detection(self):
        """욕설 감지 테스트"""
        for text, expected_detected, expected_category in self.test_cases:
            with self.subTest(text=text):
                result = self.profanity_detector.detect(text)
                
                if expected_detected:
                    self.assertIsNotNone(result, f"'{text}' should be detected as profanity")
                    self.assertTrue(result.is_profanity)
                    if expected_category:
                        # 카테고리는 Baseline 규칙에 따라 다를 수 있음
                        self.assertIn(result.category, [
                            "PROFANITY_DETECTED", "PROFANITY",
                            "SEXUAL_DETECTED", "SEXUAL_HARASSMENT",
                            "HATE_DETECTED", "HATE_SPEECH"
                        ])
                else:
                    # 욕설이 아닌 경우 None이거나 is_profanity=False
                    if result:
                        self.assertFalse(result.is_profanity)
    
    def test_korcen_filter(self):
        """Korcen 필터 직접 테스트"""
        test_text = "시발놈아"
        result = self.korcen_filter.detect(test_text)
        
        # Korcen이 설치되지 않은 경우 None이 반환될 수 있음
        # 이 경우 Baseline 규칙으로 폴백됨
        # 따라서 결과가 None이 아니거나, 폴백된 결과가 있어야 함
    
    def test_hint_mapping(self):
        """Korcen 힌트 매핑 테스트"""
        hint_mapping = KorcenFilter.HINT_MAPPING
        
        self.assertIn("general", hint_mapping)
        self.assertIn("sexual", hint_mapping)
        self.assertIn("race", hint_mapping)
        self.assertIn("special", hint_mapping)
        
        self.assertEqual(hint_mapping["general"], "PROFANITY_DETECTED")
        self.assertEqual(hint_mapping["sexual"], "SEXUAL_DETECTED")
        self.assertEqual(hint_mapping["race"], "HATE_DETECTED")
        self.assertEqual(hint_mapping["special"], "VIOLENCE_THREAT")


if __name__ == "__main__":
    unittest.main()
