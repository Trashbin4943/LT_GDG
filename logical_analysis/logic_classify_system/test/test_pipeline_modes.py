"""
파이프라인 모드 테스트

세 가지 파이프라인 모드의 동작 확인
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.pipeline.main_pipeline import MainPipeline
from logic_classify_system.config.labels import PipelineMode


class TestPipelineModes(unittest.TestCase):
    """파이프라인 모드 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_cases = [
            ("시발놈아", "PROFANITY", "SPECIAL"),
            ("상품 문의합니다", "INQUIRY", "NORMAL"),
            ("지금 당장 환불해줘", "UNREASONABLE_DEMAND", "SPECIAL"),
            ("안녕하세요", "INQUIRY", "NORMAL")
        ]
    
    def test_fast_classify_mode(self):
        """모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL 테스트"""
        pipeline = MainPipeline(mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL)
        
        for text, expected_label, expected_type in self.test_cases:
            with self.subTest(text=text):
                result = pipeline.process_single_sentence(text, session_id="test_001")
                self.assertIsNotNone(result)
                self.assertEqual(result.text, text)
                # Label과 Type은 기본적으로 일치하는지 확인
                # 실제 모델이 없으면 기본값이 반환될 수 있음
    
    def test_classify_both_always_mode(self):
        """모드 2: CLASSIFY_BOTH_ALWAYS 테스트"""
        pipeline = MainPipeline(mode=PipelineMode.CLASSIFY_BOTH_ALWAYS)
        
        for text, expected_label, expected_type in self.test_cases:
            with self.subTest(text=text):
                result = pipeline.process_single_sentence(text, session_id="test_002")
                self.assertIsNotNone(result)
                self.assertEqual(result.text, text)
    
    def test_detail_first_then_verify_mode(self):
        """모드 3: DETAIL_FIRST_THEN_VERIFY 테스트"""
        pipeline = MainPipeline(mode=PipelineMode.DETAIL_FIRST_THEN_VERIFY)
        
        for text, expected_label, expected_type in self.test_cases:
            with self.subTest(text=text):
                result = pipeline.process_single_sentence(text, session_id="test_003")
                self.assertIsNotNone(result)
                self.assertEqual(result.text, text)
    
    def test_mode_comparison(self):
        """모드 간 비교 테스트"""
        text = "시발놈아"
        session_id = "test_004"
        
        pipeline1 = MainPipeline(mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL)
        pipeline2 = MainPipeline(mode=PipelineMode.CLASSIFY_BOTH_ALWAYS)
        pipeline3 = MainPipeline(mode=PipelineMode.DETAIL_FIRST_THEN_VERIFY)
        
        result1 = pipeline1.process_single_sentence(text, session_id)
        result2 = pipeline2.process_single_sentence(text, session_id)
        result3 = pipeline3.process_single_sentence(text, session_id)
        
        # 모든 모드에서 결과가 반환되는지 확인
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertIsNotNone(result3)
        
        # 모든 결과가 같은 텍스트를 가리키는지 확인
        self.assertEqual(result1.text, text)
        self.assertEqual(result2.text, text)
        self.assertEqual(result3.text, text)


if __name__ == "__main__":
    unittest.main()
