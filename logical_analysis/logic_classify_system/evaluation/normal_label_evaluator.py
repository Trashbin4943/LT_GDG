"""
Normal Label 평가 프레임워크

상담사가 시스템 매뉴얼에 따라 적절히 대응했는지 평가 (HEAD 기반)
Normal Label의 품질 평가, 점수 계산 및 피드백 생성 (logic 기능 통합)
"""

from typing import List, Dict, Optional
from datetime import datetime
import logging

# HEAD: 기존 import 유지
try:
    from .evaluation_result import EvaluationResult
    from .manual_checker import ManualChecker
except ImportError:
    # logic: data_structures에서 import
    from ..data.data_structures import EvaluationResult
    ManualChecker = None

from ..data.data_structures import ClassificationResult
from ..config.labels import NormalLabel

logger = logging.getLogger(__name__)


class NormalLabelEvaluator:
    """Normal Label 평가 프레임워크 (HEAD 기반 + logic 기능 통합)"""
    
    # 평가 기준 가중치 (HEAD: SCORING_WEIGHTS 유지)
    SCORING_WEIGHTS = {
        "information_accuracy": 0.3,
        "manual_compliance": 0.3,
        "communication_clarity": 0.2,
        "empathy": 0.1,
        "problem_solving": 0.1
    }
    
    # logic: CRITERIA_WEIGHTS도 유지 (호환성)
    CRITERIA_WEIGHTS = {
        "appropriateness": 0.25,
        "clarity": 0.25,
        "context_match": 0.25,
        "response_quality": 0.25
    }
    
    def __init__(self, manual_path: Optional[str] = None):
        """
        평가 프레임워크 초기화
        
        Args:
            manual_path: 매뉴얼 JSON 파일 경로 (향후 구현)
        """
        # HEAD: ManualChecker 사용
        if ManualChecker:
            self.manual_checker = ManualChecker(manual_path)
        else:
            self.manual_checker = None
    
    def evaluate(
        self,
        label: Optional[str] = None,
        customer_text: Optional[str] = None,
        agent_text: Optional[str] = None,
        session_context: Optional[List[str]] = None,
        classification_result: Optional[ClassificationResult] = None
    ) -> EvaluationResult:
        """
        Normal Label 평가 (HEAD 메서드 시그니처 유지 + logic 호환성)
        
        Args:
            label: Normal Label (HEAD 방식)
            customer_text: 고객 발화 (HEAD 방식)
            agent_text: 상담사 발화 (HEAD 방식)
            session_context: 세션 맥락 (HEAD 방식)
            classification_result: 분류 결과 (logic 방식)
        
        Returns:
            EvaluationResult
        """
        # logic 방식 지원
        if classification_result:
            if classification_result.label_type != "NORMAL":
                raise ValueError(f"Normal Label만 평가 가능합니다. 받은 label_type: {classification_result.label_type}")
            
            label = classification_result.label
            customer_text = classification_result.text
            agent_text = None  # logic에서는 선택사항
        
        # HEAD 방식: 필수 파라미터 확인
        if not label:
            raise ValueError("label 또는 classification_result가 필요합니다.")
        
        # 평가 기준 가져오기 (HEAD 방식)
        criteria = self._get_criteria(label)
        
        # 각 기준별 점수 계산 (HEAD 방식)
        criteria_scores = {}
        for criterion in criteria:
            if customer_text and agent_text:
                score = self._evaluate_criterion(
                    criterion, label, customer_text, agent_text, session_context or []
                )
            else:
                # logic 방식: 간단한 점수 계산
                score = self._calculate_simple_score(criterion, label, classification_result)
            criteria_scores[criterion] = score
        
        # 종합 점수 계산 (HEAD 방식)
        total_score = self._calculate_total_score(criteria_scores, criteria)
        
        # 피드백 생성 (HEAD 방식)
        feedback = self._generate_feedback(label, criteria_scores, total_score)
        
        # 개선 제안 생성 (HEAD 방식)
        recommendations = self._generate_recommendations(label, criteria_scores)
        
        return EvaluationResult(
            label=label,
            score=total_score,
            criteria_scores=criteria_scores,
            feedback=feedback,
            text=customer_text or (classification_result.text if classification_result else None),
            timestamp=datetime.now()
        )
    
    def _get_criteria(self, label: str) -> List[str]:
        """
        Label별 평가 기준 반환 (HEAD: 유지)
        
        Args:
            label: Normal Label
        
        Returns:
            평가 기준 리스트
        """
        criteria_map = {
            "INQUIRY": ["information_accuracy", "manual_compliance", "communication_clarity"],
            "COMPLAINT": ["empathy", "problem_solving", "manual_compliance"],
            "REQUEST": ["manual_compliance", "problem_solving", "communication_clarity"],
            "CLARIFICATION": ["communication_clarity", "empathy", "information_accuracy"],
            "CONFIRMATION": ["information_accuracy", "communication_clarity"],
            "CLOSING": ["manual_compliance", "communication_clarity"]
        }
        return criteria_map.get(label, ["manual_compliance", "communication_clarity"])
    
    def _evaluate_criterion(
        self,
        criterion: str,
        label: str,
        customer_text: str,
        agent_text: str,
        session_context: List[str]
    ) -> float:
        """
        개별 기준 평가 (HEAD: 유지)
        
        Returns:
            점수 (0.0-1.0)
        """
        if criterion == "manual_compliance" and self.manual_checker:
            return self.manual_checker.check_compliance(label, agent_text)
        elif criterion == "information_accuracy":
            return self._check_information_accuracy(label, agent_text)
        elif criterion == "communication_clarity":
            return self._check_communication_clarity(label, agent_text)
        elif criterion == "empathy":
            return self._check_empathy(label, agent_text, customer_text)
        elif criterion == "problem_solving":
            return self._check_problem_solving(label, agent_text, customer_text)
        else:
            return 0.5
    
    def _calculate_simple_score(
        self,
        criterion: str,
        label: str,
        classification_result: Optional[ClassificationResult]
    ) -> float:
        """
        간단한 점수 계산 (logic 방식 호환)
        """
        if not classification_result:
            return 0.5
        
        # logic 방식의 점수 계산 로직
        if criterion == "appropriateness":
            return min(1.0, classification_result.confidence)
        elif criterion == "clarity":
            text = classification_result.text or ""
            length = len(text.strip())
            if length < 5:
                return 0.5
            elif length < 20:
                return 0.7
            elif length < 100:
                return 0.85
            else:
                return 0.9
        elif criterion == "context_match":
            return 0.8
        elif criterion == "response_quality":
            return min(1.0, classification_result.confidence * 0.9)
        else:
            return 0.5
    
    def _check_information_accuracy(self, label: str, agent_text: str) -> float:
        """정보 제공 정확성 확인 (HEAD: 유지)"""
        required_keywords = {
            "INQUIRY": ["안내", "확인", "정보"],
            "COMPLAINT": ["불편", "사과", "해결"],
            "REQUEST": ["처리", "절차", "안내"]
        }
        
        keywords = required_keywords.get(label, [])
        if not keywords:
            return 0.7
        
        agent_lower = agent_text.lower()
        found_count = sum(1 for kw in keywords if kw in agent_lower)
        
        if found_count == 0:
            return 0.3
        elif found_count == len(keywords):
            return 1.0
        else:
            return 0.5 + (found_count / len(keywords)) * 0.3
    
    def _check_communication_clarity(self, label: str, agent_text: str) -> float:
        """소통 명확성 확인 (HEAD: 유지)"""
        if not agent_text:
            return 0.0
        
        words = agent_text.split()
        if len(words) < 3:
            return 0.4
        elif len(words) > 50:
            return 0.6
        else:
            return 0.8
    
    def _check_empathy(self, label: str, agent_text: str, customer_text: str) -> float:
        """공감 능력 확인 (HEAD: 유지)"""
        empathy_keywords = ["죄송", "불편", "이해", "공감", "안타깝"]
        agent_lower = agent_text.lower()
        
        found_count = sum(1 for kw in empathy_keywords if kw in agent_lower)
        
        if found_count == 0:
            return 0.3
        elif found_count >= 2:
            return 1.0
        else:
            return 0.6
    
    def _check_problem_solving(self, label: str, agent_text: str, customer_text: str) -> float:
        """문제 해결 능력 확인 (HEAD: 유지)"""
        solution_keywords = ["해결", "방안", "제시", "처리", "조치", "대안"]
        agent_lower = agent_text.lower()
        
        found_count = sum(1 for kw in solution_keywords if kw in agent_lower)
        
        if found_count == 0:
            return 0.3
        elif found_count >= 2:
            return 1.0
        else:
            return 0.6
    
    def _calculate_total_score(
        self,
        criteria_scores: Dict[str, float],
        criteria: List[str]
    ) -> float:
        """
        종합 점수 계산 (가중치 적용) (HEAD: 유지)
        
        Returns:
            종합 점수 (0-100)
        """
        total = 0.0
        for criterion in criteria:
            weight = self.SCORING_WEIGHTS.get(criterion, 0.1)
            total += criteria_scores.get(criterion, 0.0) * weight
        
        return total * 100
    
    def _generate_feedback(
        self,
        label: str,
        criteria_scores: Dict[str, float],
        total_score: float
    ) -> str:
        """피드백 생성 (HEAD: 유지)"""
        if total_score >= 80:
            return f"{label} 상황에서 우수한 대응을 보여주셨습니다."
        elif total_score >= 60:
            return f"{label} 상황에서 양호한 대응을 보여주셨습니다. 일부 개선이 필요합니다."
        else:
            return f"{label} 상황에서 대응이 미흡합니다. 매뉴얼을 다시 확인해주세요."
    
    def _generate_recommendations(
        self,
        label: str,
        criteria_scores: Dict[str, float]
    ) -> List[str]:
        """개선 제안 생성 (HEAD: 유지)"""
        recommendations = []
        
        for criterion, score in criteria_scores.items():
            if score < 0.5:
                if criterion == "manual_compliance":
                    recommendations.append("매뉴얼에 명시된 절차를 다시 확인해주세요.")
                elif criterion == "information_accuracy":
                    recommendations.append("정확한 정보를 제공하도록 주의해주세요.")
                elif criterion == "communication_clarity":
                    recommendations.append("명확하고 이해하기 쉬운 설명을 해주세요.")
                elif criterion == "empathy":
                    recommendations.append("고객의 감정을 인식하고 공감 표현을 사용해주세요.")
                elif criterion == "problem_solving":
                    recommendations.append("구체적인 해결 방안을 제시해주세요.")
        
        if not recommendations:
            recommendations.append("현재 대응이 적절합니다. 계속 유지해주세요.")
        
        return recommendations
