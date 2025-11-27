"""
IntensityRegressionModel 단위 테스트
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.models.intensity_regression_model import IntensityRegressionModel
from logical_analysis.logic_classify_system.test.fixtures.mock_models import MockIntensityRegressionModel
from logical_analysis.logic_classify_system.test.fixtures.test_data import TEST_CASES


class TestIntensityRegressionModel(unittest.TestCase):
    """IntensityRegressionModel 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_model_path = "test/path/to/model"
    
    def test_model_initialization_with_mock(self):
        """Mock 모델 초기화 테스트"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        self.assertIsNotNone(mock_model)
        self.assertTrue(mock_model.is_available())
        self.assertEqual(mock_model.device, "cpu")
    
    def test_model_initialization_without_path(self):
        """모델 경로 없을 때 초기화 테스트"""
        # 실제 모델 경로가 없을 때 graceful degradation
        with patch('logical_analysis.logic_classify_system.models.intensity_regression_model.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            # transformers가 없을 때 처리
            with patch('logical_analysis.logic_classify_system.models.intensity_regression_model.TRANSFORMERS_AVAILABLE', False):
                model = IntensityRegressionModel("nonexistent/path")
                self.assertFalse(model.is_available())
    
    def test_predict_normal_text(self):
        """정상 텍스트 예측 테스트"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        test_case = TEST_CASES['normal_inquiry']
        result = mock_model.predict(test_case['text'])
        
        self.assertIn('intensity', result)
        self.assertIn('is_immoral', result)
        self.assertIn('immorality_confidence', result)
        
        # 정상 텍스트는 intensity가 0.0에 가까워야 함
        self.assertGreaterEqual(result['intensity'], 0.0)
        self.assertLessEqual(result['intensity'], 3.0)
    
    def test_predict_profanity_text(self):
        """욕설 포함 텍스트 예측 테스트"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        test_case = TEST_CASES['profanity_high']
        result = mock_model.predict(test_case['text'])
        
        # 욕설이 있으면 intensity가 높아야 함
        self.assertGreater(result['intensity'], 0.0)
        self.assertLessEqual(result['intensity'], 3.0)
        self.assertTrue(result['is_immoral'])
        self.assertGreater(result['immorality_confidence'], 0.0)
    
    def test_predict_intensity_range(self):
        """Intensity 범위 검증 (0.0 ~ 3.0)"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        test_texts = [
            '안녕하세요',
            '불만이 있습니다',
            '시발놈아',
            '죽여버릴거야'
        ]
        
        for text in test_texts:
            result = mock_model.predict(text)
            intensity = result['intensity']
            
            self.assertGreaterEqual(intensity, 0.0, f"Intensity는 0.0 이상이어야 합니다: {intensity}")
            self.assertLessEqual(intensity, 3.0, f"Intensity는 3.0 이하여야 합니다: {intensity}")
    
    def test_predict_empty_text(self):
        """빈 텍스트 입력 테스트"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        result = mock_model.predict("")
        
        # 빈 텍스트는 기본값 반환
        self.assertIn('intensity', result)
        self.assertIn('is_immoral', result)
        self.assertIn('immorality_confidence', result)
    
    def test_predict_long_text(self):
        """매우 긴 텍스트 입력 테스트 (truncation 처리)"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        long_text = "안녕하세요 " * 1000  # 매우 긴 텍스트
        
        result = mock_model.predict(long_text, max_length=128)
        
        # truncation이 되어도 정상적으로 처리되어야 함
        self.assertIn('intensity', result)
        self.assertIn('is_immoral', result)
    
    def test_is_immoral_logic(self):
        """is_immoral 판단 로직 테스트"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        # intensity > 0인 경우
        result = mock_model.predict("시발놈아")
        self.assertTrue(result['is_immoral'])
        
        # intensity = 0인 경우
        result = mock_model.predict("안녕하세요")
        # Mock 모델의 로직에 따라 다를 수 있음
        self.assertIn('is_immoral', result)
    
    def test_immorality_confidence_calculation(self):
        """immorality_confidence 계산 검증"""
        mock_model = MockIntensityRegressionModel(self.test_model_path)
        
        result = mock_model.predict("시발놈아")
        
        # immorality_confidence는 0.0 ~ 1.0 범위
        self.assertGreaterEqual(result['immorality_confidence'], 0.0)
        self.assertLessEqual(result['immorality_confidence'], 1.0)
        
        # intensity가 높을수록 confidence도 높아야 함
        if result['is_immoral']:
            expected_min_confidence = result['intensity'] / 3.0 * 0.8  # 약간의 여유
            self.assertGreaterEqual(result['immorality_confidence'], expected_min_confidence)


class TestIntensityRegressionModelWithRealModel(unittest.TestCase):
    """실제 모델이 있을 때 테스트 (선택적)"""
    
    @unittest.skip("실제 모델이 없을 수 있으므로 스킵")
    def test_real_model_loading(self):
        """실제 모델 로딩 테스트 (모델이 있을 때만 실행)"""
        from logical_analysis.logic_classify_system.config.model_paths import get_intensity_model_path
        
        model_path = get_intensity_model_path()
        if model_path:
            model = IntensityRegressionModel(model_path)
            self.assertTrue(model.is_available())
        else:
            self.skipTest("모델 경로가 없습니다")


if __name__ == '__main__':
    unittest.main()

