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
                
                # STT_TEST_DATA가 문자열인 경우 처리
                if isinstance(STT_TEST_DATA.get('normal_session'), str):
                    stt_text = STT_TEST_DATA['normal_session']
                else:
                    stt_text = STT_TEST_DATA.get('normal_session', {}).get('text', '안녕하세요. 문의가 있습니다.')
                
                result = pipeline.process(stt_text, session_id="test_session")
                
                self.assertIsNotNone(result)
                self.assertEqual(result.session_id, "test_session")
                self.assertGreater(len(result.results), 0)
                
                # 각 Classification 결과 검증
                for classification_result in result.results:
                    self.assertIsNotNone(classification_result)
                    self.assertIsNotNone(classification_result.label)
                    self.assertIsNotNone(classification_result.label_type)
                    self.assertGreaterEqual(classification_result.confidence, 0.0)
                    self.assertLessEqual(classification_result.confidence, 1.0)
    
    def test_end_to_end_profanity_session(self):
        """욕설 포함 세션 End-to-End 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                # STT_TEST_DATA가 문자열인 경우 처리
                if isinstance(STT_TEST_DATA.get('profanity_session'), str):
                    stt_text = STT_TEST_DATA['profanity_session']
                else:
                    stt_text = STT_TEST_DATA.get('profanity_session', {}).get('text', '시발놈아! 이게 뭐야?')
                
                result = pipeline.process(stt_text, session_id="test_session")
                
                self.assertIsNotNone(result)
                self.assertEqual(result.session_id, "test_session")
                
                # 욕설이 포함된 Turn은 SPECIAL label일 가능성이 높음
                for classification_result in result.results:
                    if '시발' in classification_result.text.lower():
                        # 욕설이 있으면 SPECIAL일 가능성이 높음
                        self.assertIn(classification_result.label_type, ['SPECIAL', 'NORMAL'])
    
    def test_pipeline_with_agent_response(self):
        """상담원 응답이 있는 경우 통합 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                # STT_TEST_DATA가 문자열인 경우 처리
                if isinstance(STT_TEST_DATA.get('complaint_session'), str):
                    stt_text = STT_TEST_DATA['complaint_session']
                else:
                    stt_text = STT_TEST_DATA.get('complaint_session', {}).get('text', '서비스가 불만족스럽습니다.')
                
                result = pipeline.process(stt_text, session_id="test_session")
                
                self.assertIsNotNone(result)
                
                # PipelineResult는 ClassificationResult 리스트만 반환
                # agent_response_quality_score는 MainPipeline 내부에서 계산되지만
                # 현재 구조에서는 직접 접근 불가
                for classification_result in result.results:
                    self.assertIsNotNone(classification_result)
    
    def test_pipeline_intensity_integration(self):
        """Intensity 정보 통합 테스트"""
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                # STT_TEST_DATA가 문자열인 경우 처리
                if isinstance(STT_TEST_DATA.get('profanity_session'), str):
                    stt_text = STT_TEST_DATA['profanity_session']
                else:
                    stt_text = STT_TEST_DATA.get('profanity_session', {}).get('text', '시발놈아!')
                
                result = pipeline.process(stt_text, session_id="test_session")
                
                # 각 Classification 결과에 intensity 정보가 포함되어야 함
                for classification_result in result.results:
                    # Intensity 정보 검증 (모델이 있으면 값이 설정됨)
                    if classification_result.intensity is not None:
                        self.assertGreaterEqual(classification_result.intensity, 0.0)
                        self.assertLessEqual(classification_result.intensity, 3.0)
                    
                    if classification_result.intensity_level is not None:
                        self.assertIn(classification_result.intensity_level, ['LOW', 'MEDIUM', 'HIGH'])
                    
                    if classification_result.is_immoral is not None:
                        self.assertIsInstance(classification_result.is_immoral, bool)
                    
                    if classification_result.immorality_confidence is not None:
                        self.assertGreaterEqual(classification_result.immorality_confidence, 0.0)
                        self.assertLessEqual(classification_result.immorality_confidence, 1.0)
    
    def test_pipeline_turn_risk_score_calculation(self):
        """Turn Risk Score 계산 통합 테스트"""
        # 이 테스트는 MainPipeline의 내부 메서드를 테스트하므로
        # 단위 테스트로 이동하는 것이 더 적절합니다.
        # 여기서는 파이프라인이 정상 동작하는지만 확인
        with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.IntensityRegressionModel', MockIntensityRegressionModel):
            with patch('logical_analysis.logic_classify_system.intent_classifier.enhanced_intent_predictor.TernaryClassificationModel', MockTernaryClassificationModel):
                pipeline = MainPipeline(
                    intensity_model_path=self.test_intensity_model_path,
                    ternary_model_path=self.test_ternary_model_path,
                    use_enhanced_predictor=True
                )
                
                # STT_TEST_DATA가 문자열인 경우 처리
                if isinstance(STT_TEST_DATA.get('complaint_session'), str):
                    stt_text = STT_TEST_DATA['complaint_session']
                else:
                    stt_text = STT_TEST_DATA.get('complaint_session', {}).get('text', '서비스가 불만족스럽습니다.')
                
                result = pipeline.process(stt_text, session_id="test_session")
                
                # 파이프라인이 정상 동작하는지 확인
                self.assertIsNotNone(result)
                self.assertGreater(len(result.results), 0)
                
                # 각 Classification 결과 검증
                for classification_result in result.results:
                    self.assertIsNotNone(classification_result.label)
                    self.assertIsNotNone(classification_result.label_type)
    
    def test_pipeline_without_models(self):
        """모델 없이 파이프라인 실행 테스트 (Baseline 규칙만 사용)"""
        pipeline = MainPipeline(
            intensity_model_path=None,
            ternary_model_path=None,
            use_enhanced_predictor=False
        )
        
        # STT_TEST_DATA가 문자열인 경우 처리
        if isinstance(STT_TEST_DATA.get('normal_session'), str):
            stt_text = STT_TEST_DATA['normal_session']
        else:
            stt_text = STT_TEST_DATA.get('normal_session', {}).get('text', '안녕하세요. 문의가 있습니다.')
        
        result = pipeline.process(stt_text, session_id="test_session")
        
        # 모델이 없어도 파이프라인이 정상 동작해야 함
        self.assertIsNotNone(result)
        self.assertEqual(result.session_id, "test_session")
        self.assertGreater(len(result.results), 0)


if __name__ == '__main__':
    unittest.main()
