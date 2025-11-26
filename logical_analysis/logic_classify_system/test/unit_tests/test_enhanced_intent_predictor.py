"""
EnhancedIntentPredictor 단위 테스트
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor
from logical_analysis.logic_classify_system.test.fixtures.mock_models import (
    MockIntensityRegressionModel,
    MockTernaryClassificationModel
)
from logical_analysis.logic_classify_system.test.fixtures.test_data import TEST_CASES


class TestEnhancedIntentPredictor(unittest.TestCase):
    """EnhancedIntentPredictor 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_intensity_model_path = "test/path/to/intensity/model"
        self.test_ternary_model_path = "test/path/to/ternary/model"
    
    def test_initialization_with_mock_models(self):
        """Mock 모델로 초기화 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                predictor = EnhancedIntentPredictor(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_models=True
                )
                
                self.assertIsNotNone(predictor)
                self.assertIsNotNone(predictor.baseline_rules)
    
    def test_initialization_without_models(self):
        """모델 없이 초기화 테스트 (Baseline 규칙만 사용)"""
        predictor = EnhancedIntentPredictor(
            intensity_model_path=None,
            ternary_model_path=None,
            use_models=False
        )
        
        self.assertIsNotNone(predictor)
        self.assertIsNone(predictor.intensity_model)
        self.assertIsNone(predictor.ternary_model)
        self.assertIsNotNone(predictor.baseline_rules)
    
    def test_predict_with_profanity(self):
        """욕설 감지 시 예측 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                predictor = EnhancedIntentPredictor(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_models=True
                )
                
                result = predictor.predict(
                    text="시발놈아!",
                    profanity_detected=True,
                    profanity_confidence=0.9
                )
                
                self.assertIsNotNone(result)
                self.assertEqual(result.label_type, "SPECIAL")
                self.assertGreater(result.confidence, 0.0)
    
    def test_predict_with_intensity_model(self):
        """Intensity 모델을 사용한 예측 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            predictor = EnhancedIntentPredictor(
                intensity_model_path=self.test_intensity_model_path,
                ternary_model_path=None,
                use_models=True
            )
            
            test_case = TEST_CASES['profanity_high']
            result = predictor.predict(
                text=test_case['text'],
                profanity_detected=False,
                profanity_confidence=0.0
            )
            
            self.assertIsNotNone(result)
            self.assertGreaterEqual(result.intensity, 0.0)
            self.assertLessEqual(result.intensity, 3.0)
            self.assertIsNotNone(result.is_immoral)
            self.assertGreaterEqual(result.immorality_confidence, 0.0)
            self.assertLessEqual(result.immorality_confidence, 1.0)
    
    def test_predict_with_ternary_model(self):
        """3진 분류 모델을 사용한 예측 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
            predictor = EnhancedIntentPredictor(
                intensity_model_path=None,
                ternary_model_path=self.test_ternary_model_path,
                use_models=True
            )
            
            test_case = TEST_CASES['profanity_high']
            result = predictor.predict(
                text=test_case['text'],
                profanity_detected=False,
                profanity_confidence=0.0
            )
            
            self.assertIsNotNone(result)
            self.assertIn(result.intensity_level, ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'])
    
    def test_predict_with_both_models(self):
        """두 모델 모두 사용한 예측 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                predictor = EnhancedIntentPredictor(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_models=True
                )
                
                test_case = TEST_CASES['profanity_high']
                result = predictor.predict(
                    text=test_case['text'],
                    profanity_detected=False,
                    profanity_confidence=0.0
                )
                
                # 두 모델의 결과가 모두 포함되어야 함
                self.assertIsNotNone(result)
                self.assertGreaterEqual(result.intensity, 0.0)
                self.assertLessEqual(result.intensity, 3.0)
                self.assertIn(result.intensity_level, ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'])
    
    def test_predict_normal_text(self):
        """정상 텍스트 예측 테스트"""
        predictor = EnhancedIntentPredictor(
            intensity_model_path=None,
            ternary_model_path=None,
            use_models=False  # Baseline 규칙만 사용
        )
        
        test_case = TEST_CASES['normal_inquiry']
        result = predictor.predict(
            text=test_case['text'],
            profanity_detected=False,
            profanity_confidence=0.0
        )
        
        self.assertIsNotNone(result)
        # 정상 텍스트는 NORMAL일 가능성이 높음
        # (Baseline 규칙에 따라 다를 수 있음)
        self.assertIn(result.label_type, ['NORMAL', 'SPECIAL', 'UNKNOWN'])
    
    def test_predict_intensity_in_range(self):
        """Intensity가 0.0 ~ 3.0 범위인지 검증"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            predictor = EnhancedIntentPredictor(
                intensity_model_path=self.test_intensity_model_path,
                ternary_model_path=None,
                use_models=True
            )
            
            test_texts = [
                '안녕하세요',
                '불만이 있습니다',
                '시발놈아'
            ]
            
            for text in test_texts:
                result = predictor.predict(
                    text=text,
                    profanity_detected=False,
                    profanity_confidence=0.0
                )
                
                self.assertGreaterEqual(result.intensity, 0.0, f"Intensity는 0.0 이상이어야 합니다: {result.intensity}")
                self.assertLessEqual(result.intensity, 3.0, f"Intensity는 3.0 이하여야 합니다: {result.intensity}")
    
    def test_predict_intensity_level_valid(self):
        """intensity_level이 유효한 값인지 검증"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
            predictor = EnhancedIntentPredictor(
                intensity_model_path=None,
                ternary_model_path=self.test_ternary_model_path,
                use_models=True
            )
            
            test_texts = [
                '안녕하세요',
                '불만이 있습니다',
                '시발놈아'
            ]
            
            valid_levels = ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN']
            
            for text in test_texts:
                result = predictor.predict(
                    text=text,
                    profanity_detected=False,
                    profanity_confidence=0.0
                )
                
                self.assertIn(result.intensity_level, valid_levels, f"유효하지 않은 intensity_level: {result.intensity_level}")
    
    def test_predict_immorality_confidence_range(self):
        """immorality_confidence가 0.0 ~ 1.0 범위인지 검증"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            predictor = EnhancedIntentPredictor(
                intensity_model_path=self.test_intensity_model_path,
                ternary_model_path=None,
                use_models=True
            )
            
            result = predictor.predict(
                text="테스트 텍스트",
                profanity_detected=False,
                profanity_confidence=0.0
            )
            
            self.assertGreaterEqual(result.immorality_confidence, 0.0)
            self.assertLessEqual(result.immorality_confidence, 1.0)


if __name__ == '__main__':
    unittest.main()

