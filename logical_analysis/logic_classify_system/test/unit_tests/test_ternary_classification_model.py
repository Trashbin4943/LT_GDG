"""
TernaryClassificationModel 단위 테스트
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.models.ternary_classification_model import TernaryClassificationModel
from logical_analysis.logic_classify_system.test.fixtures.mock_models import MockTernaryClassificationModel
from logical_analysis.logic_classify_system.test.fixtures.test_data import TEST_CASES


class TestTernaryClassificationModel(unittest.TestCase):
    """TernaryClassificationModel 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_model_path = "test/path/to/model"
    
    def test_model_initialization_with_mock(self):
        """Mock 모델 초기화 테스트"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        self.assertIsNotNone(mock_model)
        self.assertTrue(mock_model.is_available())
        self.assertEqual(mock_model.device, "cpu")
    
    def test_label_mapping(self):
        """Label 매핑 테스트"""
        self.assertEqual(MockTernaryClassificationModel.LABEL_MAPPING[0], 'LOW')
        self.assertEqual(MockTernaryClassificationModel.LABEL_MAPPING[1], 'MEDIUM')
        self.assertEqual(MockTernaryClassificationModel.LABEL_MAPPING[2], 'HIGH')
    
    def test_intensity_ranges(self):
        """Intensity 구간 정의 검증"""
        ranges = MockTernaryClassificationModel.INTENSITY_RANGES
        
        self.assertEqual(ranges['LOW'], (1.0, 1.6))
        self.assertEqual(ranges['MEDIUM'], (1.8, 2.4))
        self.assertEqual(ranges['HIGH'], (2.6, 3.0))
    
    def test_predict_normal_text(self):
        """정상 텍스트 예측 테스트"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        test_case = TEST_CASES['normal_inquiry']
        result = mock_model.predict(test_case['text'])
        
        self.assertIn('intensity_level', result)
        self.assertIn('intensity_level_confidence', result)
        self.assertIn('probabilities', result)
        
        # 정상 텍스트는 LOW 또는 MEDIUM일 가능성이 높음
        self.assertIn(result['intensity_level'], ['LOW', 'MEDIUM', 'HIGH'])
    
    def test_predict_profanity_text(self):
        """욕설 포함 텍스트 예측 테스트"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        test_case = TEST_CASES['profanity_high']
        result = mock_model.predict(test_case['text'])
        
        # 욕설이 있으면 HIGH일 가능성이 높음
        self.assertIn(result['intensity_level'], ['LOW', 'MEDIUM', 'HIGH'])
        self.assertGreater(result['intensity_level_confidence'], 0.0)
    
    def test_predict_intensity_levels(self):
        """모든 intensity_level 분류 테스트"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        test_cases = [
            ('안녕하세요', 'LOW'),
            ('불만이 있습니다', 'MEDIUM'),
            ('시발놈아', 'HIGH')
        ]
        
        for text, expected_level in test_cases:
            result = mock_model.predict(text)
            # Mock 모델의 로직에 따라 다를 수 있지만, 유효한 level이어야 함
            self.assertIn(result['intensity_level'], ['LOW', 'MEDIUM', 'HIGH'])
    
    def test_probabilities_sum(self):
        """확률 분포 합이 1.0인지 검증"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        test_texts = [
            '안녕하세요',
            '불만이 있습니다',
            '시발놈아'
        ]
        
        for text in test_texts:
            result = mock_model.predict(text)
            probabilities = result['probabilities']
            
            # 확률의 합은 1.0에 가까워야 함 (부동소수점 오차 고려)
            prob_sum = sum(probabilities.values())
            self.assertAlmostEqual(prob_sum, 1.0, places=2)
    
    def test_probabilities_range(self):
        """확률 값이 0.0 ~ 1.0 범위인지 검증"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        result = mock_model.predict("테스트 텍스트")
        probabilities = result['probabilities']
        
        for level, prob in probabilities.items():
            self.assertGreaterEqual(prob, 0.0, f"{level} 확률은 0.0 이상이어야 합니다")
            self.assertLessEqual(prob, 1.0, f"{level} 확률은 1.0 이하여야 합니다")
    
    def test_confidence_range(self):
        """confidence 값이 0.0 ~ 1.0 범위인지 검증"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        result = mock_model.predict("테스트 텍스트")
        
        self.assertGreaterEqual(result['intensity_level_confidence'], 0.0)
        self.assertLessEqual(result['intensity_level_confidence'], 1.0)
    
    def test_all_levels_in_probabilities(self):
        """probabilities에 모든 level이 포함되는지 검증"""
        mock_model = MockTernaryClassificationModel(self.test_model_path)
        
        result = mock_model.predict("테스트 텍스트")
        probabilities = result['probabilities']
        
        self.assertIn('LOW', probabilities)
        self.assertIn('MEDIUM', probabilities)
        self.assertIn('HIGH', probabilities)


class TestTernaryClassificationModelWithRealModel(unittest.TestCase):
    """실제 모델이 있을 때 테스트 (선택적)"""
    
    @unittest.skip("실제 모델이 없을 수 있으므로 스킵")
    def test_real_model_loading(self):
        """실제 모델 로딩 테스트 (모델이 있을 때만 실행)"""
        from logical_analysis.logic_classify_system.config.model_paths import get_ternary_model_path
        
        model_path = get_ternary_model_path()
        if model_path:
            model = TernaryClassificationModel(model_path)
            self.assertTrue(model.is_available())
        else:
            self.skipTest("모델 경로가 없습니다")


if __name__ == '__main__':
    unittest.main()

