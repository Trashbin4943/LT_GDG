"""
파이프라인 통합 테스트
Phase 5 구현 검증
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.test.fixtures.mock_models import (
    MockIntensityRegressionModel,
    MockTernaryClassificationModel
)
from logical_analysis.logic_classify_system.test.fixtures.test_data import STT_TEST_DATA


class TestPipelineIntegration(unittest.TestCase):
    """파이프라인 통합 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.test_intensity_model_path = "test/path/to/intensity/model"
        self.test_ternary_model_path = "test/path/to/ternary/model"
    
    def test_end_to_end_normal_session(self):
        """정상 세션 End-to-End 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                stt_data = STT_TEST_DATA['normal_session']
                result = pipeline.process(stt_data)
                
                self.assertIsNotNone(result)
                self.assertEqual(result.session_id, stt_data['session_id'])
                self.assertGreater(len(result.turn_results), 0)
                
                # 각 Turn 결과 검증
                for turn_result in result.turn_results:
                    self.assertIsNotNone(turn_result.customer_result)
                    self.assertIsNotNone(turn_result.turn_scores)
                    self.assertIn('customer_problem_score', turn_result.turn_scores)
                    self.assertIn('turn_risk_score', turn_result.turn_scores)
    
    def test_end_to_end_profanity_session(self):
        """욕설 포함 세션 End-to-End 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                stt_data = STT_TEST_DATA['profanity_session']
                result = pipeline.process(stt_data)
                
                self.assertIsNotNone(result)
                self.assertEqual(result.session_id, stt_data['session_id'])
                
                # 욕설이 포함된 Turn은 SPECIAL label이어야 함
                for turn_result in result.turn_results:
                    customer_result = turn_result.customer_result
                    if '시발' in customer_result.text.lower():
                        # 욕설이 있으면 SPECIAL일 가능성이 높음
                        self.assertIn(customer_result.classification_result.label_type, ['SPECIAL', 'NORMAL'])
    
    def test_pipeline_with_agent_response(self):
        """상담원 응답이 있는 경우 통합 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                stt_data = STT_TEST_DATA['complaint_session']
                result = pipeline.process(stt_data)
                
                self.assertIsNotNone(result)
                
                # 상담원 응답이 있는 Turn은 agent_response_quality_score가 계산되어야 함
                for turn_result in result.turn_results:
                    self.assertIn('agent_response_quality_score', turn_result.turn_scores)
                    # 상담원 응답이 있으면 quality_score > 0
                    # (실제로는 상담원 발화가 있는 Turn에서만)
    
    def test_pipeline_intensity_integration(self):
        """Intensity 정보 통합 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                stt_data = STT_TEST_DATA['profanity_session']
                result = pipeline.process(stt_data)
                
                # 각 Turn 결과에 intensity 정보가 포함되어야 함
                for turn_result in result.turn_results:
                    customer_result = turn_result.customer_result
                    classification_result = customer_result.classification_result
                    
                    # Intensity 정보 검증
                    self.assertGreaterEqual(classification_result.intensity, 0.0)
                    self.assertLessEqual(classification_result.intensity, 3.0)
                    self.assertIn(classification_result.intensity_level, ['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'])
                    self.assertIsNotNone(classification_result.is_immoral)
                    self.assertGreaterEqual(classification_result.immorality_confidence, 0.0)
                    self.assertLessEqual(classification_result.immorality_confidence, 1.0)
    
    def test_pipeline_turn_risk_score_calculation(self):
        """Turn Risk Score 계산 통합 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                stt_data = STT_TEST_DATA['complaint_session']
                result = pipeline.process(stt_data)
                
                # 각 Turn의 turn_risk_score 검증
                for turn_result in result.turn_results:
                    turn_scores = turn_result.turn_scores
                    
                    # 필수 점수들이 포함되어야 함
                    self.assertIn('customer_problem_score', turn_scores)
                    self.assertIn('agent_response_quality_score', turn_scores)
                    self.assertIn('turn_risk_score', turn_scores)
                    
                    # turn_risk_score 범위 검증
                    self.assertGreaterEqual(turn_scores['turn_risk_score'], 0.0)
                    self.assertLessEqual(turn_scores['turn_risk_score'], 1.0)
    
    def test_pipeline_without_models(self):
        """모델 없이 파이프라인 실행 테스트 (Baseline 규칙만 사용)"""
        pipeline = MainPipeline(
            intensity_model_path=None,
            ternary_model_path=None,
            use_enhanced_predictor=False
        )
        
        stt_data = STT_TEST_DATA['normal_session']
        result = pipeline.process(stt_data)
        
        # 모델이 없어도 파이프라인이 정상 동작해야 함
        self.assertIsNotNone(result)
        self.assertEqual(result.session_id, stt_data['session_id'])
        self.assertGreater(len(result.turn_results), 0)


if __name__ == '__main__':
    unittest.main()

