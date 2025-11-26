"""
Turn Scores 계산 단위 테스트
Phase 5 구현 검증
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.data.data_structures import (
    CustomerAnalysisResult,
    AgentAnalysisResult,
    ClassificationResult,
    ProfanityResult
)
from logical_analysis.logic_classify_system.test.fixtures.test_data import TURN_SCORES_TEST_CASES
from datetime import datetime


class TestTurnScoresCalculation(unittest.TestCase):
    """Turn Scores 계산 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.pipeline = MainPipeline(
            intensity_model_path=None,
            ternary_model_path=None,
            use_enhanced_predictor=False  # Baseline 규칙만 사용
        )
    
    def _create_customer_result(self, feature_scores: dict, intensity: float = 0.0, intensity_level: str = 'LOW'):
        """CustomerAnalysisResult 생성 헬퍼"""
        classification_result = ClassificationResult(
            label="TEST",
            label_type="SPECIAL",
            confidence=0.8,
            text="테스트 텍스트",
            probabilities={},
            timestamp=datetime.now(),
            intensity=intensity,
            intensity_level=intensity_level,
            is_immoral=intensity > 0.0,
            immorality_confidence=min(intensity / 3.0, 1.0) if intensity > 0.0 else 0.0
        )
        
        return CustomerAnalysisResult(
            session_id="test",
            turn_index=0,
            text="테스트 텍스트",
            timestamp=datetime.now(),
            profanity_result=ProfanityResult(is_profanity=False, category=None, confidence=0.0, method="baseline"),
            classification_result=classification_result,
            feature_scores=feature_scores,
            extracted_features={}
        )
    
    def _create_agent_result(self, feature_scores: dict):
        """AgentAnalysisResult 생성 헬퍼"""
        return AgentAnalysisResult(
            session_id="test",
            turn_index=0,
            text="상담원 응답",
            timestamp=datetime.now(),
            corresponding_customer_label="TEST",
            emotion_label=None,
            manual_compliance_score=feature_scores.get("manual_compliance_score", 0.0),
            compliance_details={},
            feature_scores=feature_scores,
            extracted_features={}
        )
    
    def test_customer_problem_score_calculation(self):
        """customer_problem_score 계산 테스트"""
        feature_scores = {
            "profanity_score": 0.8,
            "threat_score": 0.5,
            "sexual_harassment_score": 0.0,
            "hate_speech_score": 0.0,
            "unreasonable_demand_score": 0.3,
            "repetition_keyword_score": 0.2
        }
        
        customer_result = self._create_customer_result(feature_scores)
        agent_result = None
        
        intensity_info = {
            'intensity': 0.0,
            'intensity_level': 'LOW',
            'is_immoral': False,
            'immorality_confidence': 0.0
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # customer_problem_score는 최대값이어야 함
        self.assertIn("customer_problem_score", turn_scores)
        self.assertEqual(turn_scores["customer_problem_score"], 0.8)  # max(0.8, 0.5, 0.0, 0.0, 0.3, 0.2)
    
    def test_agent_response_quality_score_calculation(self):
        """agent_response_quality_score 계산 테스트"""
        customer_result = self._create_customer_result({})
        
        agent_feature_scores = {
            "manual_compliance_score": 0.9,
            "information_accuracy_score": 0.8,
            "communication_clarity_score": 0.7,
            "empathy_score": 0.6,
            "problem_solving_score": 0.5
        }
        
        agent_result = self._create_agent_result(agent_feature_scores)
        
        intensity_info = {
            'intensity': 0.0,
            'intensity_level': 'LOW',
            'is_immoral': False,
            'immorality_confidence': 0.0
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # 가중 평균 계산: 0.9*0.3 + 0.8*0.25 + 0.7*0.2 + 0.6*0.15 + 0.5*0.1
        expected_score = 0.9*0.3 + 0.8*0.25 + 0.7*0.2 + 0.6*0.15 + 0.5*0.1
        self.assertIn("agent_response_quality_score", turn_scores)
        self.assertAlmostEqual(turn_scores["agent_response_quality_score"], expected_score, places=2)
    
    def test_turn_risk_score_with_good_agent_response(self):
        """상담원이 잘 대응한 경우 turn_risk_score 테스트"""
        test_case = TURN_SCORES_TEST_CASES['high_customer_problem_good_agent']
        
        customer_result = self._create_customer_result(
            {"profanity_score": test_case['customer_problem_score']},
            intensity=test_case.get('intensity', 2.0),
            intensity_level=test_case['intensity_level']
        )
        
        # agent_response_quality_score를 만들기 위한 feature_scores
        # quality_score = 0.9이 되도록 설정
        agent_feature_scores = {
            "manual_compliance_score": 0.9,
            "information_accuracy_score": 0.9,
            "communication_clarity_score": 0.9,
            "empathy_score": 0.9,
            "problem_solving_score": 0.9
        }
        agent_result = self._create_agent_result(agent_feature_scores)
        
        intensity_info = {
            'intensity': test_case.get('intensity', 2.0),
            'intensity_level': test_case['intensity_level'],
            'is_immoral': True,
            'immorality_confidence': 0.67
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # 예상값과 비교 (약간의 오차 허용)
        self.assertAlmostEqual(
            turn_scores["turn_risk_score"],
            test_case['expected_turn_risk_score'],
            places=2
        )
    
    def test_turn_risk_score_without_agent_response(self):
        """상담원 대응이 없는 경우 turn_risk_score 테스트"""
        test_case = TURN_SCORES_TEST_CASES['high_customer_problem_no_agent']
        
        customer_result = self._create_customer_result(
            {"profanity_score": test_case['customer_problem_score']},
            intensity=test_case.get('intensity', 2.5),
            intensity_level=test_case['intensity_level']
        )
        
        agent_result = None
        
        intensity_info = {
            'intensity': test_case.get('intensity', 2.5),
            'intensity_level': test_case['intensity_level'],
            'is_immoral': True,
            'immorality_confidence': 0.83
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # 상담원 대응이 없으면 quality_adjustment 없음
        # base_risk * intensity_multiplier
        self.assertAlmostEqual(
            turn_scores["turn_risk_score"],
            test_case['expected_turn_risk_score'],
            places=2
        )
    
    def test_turn_risk_score_with_poor_agent_response(self):
        """상담원 대응이 부족한 경우 turn_risk_score 테스트"""
        test_case = TURN_SCORES_TEST_CASES['low_customer_problem_poor_agent']
        
        customer_result = self._create_customer_result(
            {"profanity_score": test_case['customer_problem_score']},
            intensity=1.0,
            intensity_level=test_case['intensity_level']
        )
        
        # agent_response_quality_score = 0.2가 되도록 설정
        agent_feature_scores = {
            "manual_compliance_score": 0.2,
            "information_accuracy_score": 0.2,
            "communication_clarity_score": 0.2,
            "empathy_score": 0.2,
            "problem_solving_score": 0.2
        }
        agent_result = self._create_agent_result(agent_feature_scores)
        
        intensity_info = {
            'intensity': 1.0,
            'intensity_level': test_case['intensity_level'],
            'is_immoral': True,
            'immorality_confidence': 0.33
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        self.assertAlmostEqual(
            turn_scores["turn_risk_score"],
            test_case['expected_turn_risk_score'],
            places=2
        )
    
    def test_turn_risk_score_intensity_adjustment(self):
        """Intensity level에 따른 조정 테스트"""
        customer_result = self._create_customer_result(
            {"profanity_score": 0.5},
            intensity=2.5,
            intensity_level="HIGH"
        )
        
        agent_result = None
        
        # HIGH intensity
        intensity_info = {
            'intensity': 2.5,
            'intensity_level': 'HIGH',
            'is_immoral': True,
            'immorality_confidence': 0.83
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # HIGH: profanity_score=0.5, HIGH이므로 0.5*1.2=0.6, intensity=2.5/3.0=0.833
        # customer_problem_score = max(0.6, 0.833) = 0.833
        # adjusted_risk = 0.833 (상담원 대응 없음)
        # turn_risk_score = min(0.833 * 1.15, 1.0) = 0.958
        expected_high = 0.958
        self.assertAlmostEqual(turn_scores["turn_risk_score"], expected_high, places=2)
        
        # MEDIUM intensity
        intensity_info['intensity_level'] = 'MEDIUM'
        intensity_info['intensity'] = 2.0
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # MEDIUM: profanity_score=0.5, MEDIUM이므로 0.5*1.1=0.55, intensity=2.0/3.0*0.8=0.533
        # customer_problem_score = max(0.55, 0.533) = 0.55
        # adjusted_risk = 0.55 (상담원 대응 없음)
        # turn_risk_score = 0.55 * 1.05 = 0.5775
        expected_medium = 0.5775
        self.assertAlmostEqual(turn_scores["turn_risk_score"], expected_medium, places=2)
        
        # LOW intensity
        intensity_info['intensity_level'] = 'LOW'
        intensity_info['intensity'] = 1.0
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # LOW: profanity_score=0.5, LOW이므로 intensity만 추가: 1.0/3.0*0.5=0.167
        # customer_problem_score = max(0.5, 0.167) = 0.5
        # adjusted_risk = 0.5 (상담원 대응 없음)
        # turn_risk_score = 0.5 * 1.0 = 0.5
        expected_low = 0.5
        self.assertAlmostEqual(turn_scores["turn_risk_score"], expected_low, places=2)
    
    def test_turn_risk_score_max_value(self):
        """turn_risk_score가 1.0을 초과하지 않는지 테스트"""
        customer_result = self._create_customer_result(
            {"profanity_score": 1.0},  # 최대값
            intensity=3.0,
            intensity_level="HIGH"
        )
        
        agent_result = None
        
        intensity_info = {
            'intensity': 3.0,
            'intensity_level': 'HIGH',
            'is_immoral': True,
            'immorality_confidence': 1.0
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # 1.0을 초과하지 않아야 함
        self.assertLessEqual(turn_scores["turn_risk_score"], 1.0)
    
    def test_turn_risk_score_min_value(self):
        """turn_risk_score가 0.0 미만이 되지 않는지 테스트"""
        customer_result = self._create_customer_result(
            {"profanity_score": 0.1},  # 낮은 값
            intensity=0.0,
            intensity_level="LOW"
        )
        
        # 매우 좋은 상담원 대응 (quality_score = 1.0)
        agent_feature_scores = {
            "manual_compliance_score": 1.0,
            "information_accuracy_score": 1.0,
            "communication_clarity_score": 1.0,
            "empathy_score": 1.0,
            "problem_solving_score": 1.0
        }
        agent_result = self._create_agent_result(agent_feature_scores)
        
        intensity_info = {
            'intensity': 0.0,
            'intensity_level': 'LOW',
            'is_immoral': False,
            'immorality_confidence': 0.0
        }
        
        turn_scores = self.pipeline._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        # 0.0 미만이 되지 않아야 함
        self.assertGreaterEqual(turn_scores["turn_risk_score"], 0.0)


if __name__ == '__main__':
    unittest.main()

