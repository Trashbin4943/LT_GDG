"""
Normal Label 평가기

Normal Label의 품질 평가, 점수 계산 및 피드백 생성
"""
from typing import Dict, Optional
from datetime import datetime
import logging
from logic_classify_system.data.data_structures import (
    ClassificationResult,
    EvaluationResult
)
from logic_classify_system.config.labels import NormalLabel
import logging

logger = logging.getLogger(__name__)


class NormalLabelEvaluator:
    """Normal Label 평가기"""
    
    # 평가 기준 가중치
    CRITERIA_WEIGHTS = {
        "appropriateness": 0.25,
        "clarity": 0.25,
        "context_match": 0.25,
        "response_quality": 0.25
    }
    
    def __init__(self):
        """초기화"""
        pass
    
    def evaluate(
        self,
        classification_result: ClassificationResult,
        agent_text: Optional[str] = None
    ) -> EvaluationResult:
        """
        Normal Label 평가
        
        Args:
            classification_result: 분류 결과 (label_type="NORMAL")
            agent_text: 상담사 응답 텍스트 (선택사항)
        
        Returns:
            EvaluationResult
        """
        if classification_result.label_type != "NORMAL":
            raise ValueError(f"Normal Label만 평가 가능합니다. 받은 label_type: {classification_result.label_type}")
        
        # 기준별 점수 계산
        criteria_scores = self._calculate_criteria_scores(
            classification_result,
            agent_text
        )
        
        # 전체 점수 계산 (가중 평균)
        total_score = sum(
            criteria_scores.get(criteria, 0.0) * weight
            for criteria, weight in self.CRITERIA_WEIGHTS.items()
        )
        
        # 피드백 생성
        feedback = self._generate_feedback(
            classification_result.label,
            criteria_scores,
            total_score
        )
        
        return EvaluationResult(
            label=classification_result.label,
            score=total_score,
            criteria_scores=criteria_scores,
            feedback=feedback,
            text=classification_result.text,
            timestamp=datetime.now()
        )
    
    def _calculate_criteria_scores(
        self,
        classification_result: ClassificationResult,
        agent_text: Optional[str] = None
    ) -> Dict[str, float]:
        """
        기준별 점수 계산
        
        Args:
            classification_result: 분류 결과
            agent_text: 상담사 응답 텍스트
        
        Returns:
            기준별 점수 딕셔너리
        """
        label = classification_result.label
        text = classification_result.text
        confidence = classification_result.confidence
        
        scores = {}
        
        # 1. 적절성 (Appropriateness)
        scores["appropriateness"] = self._score_appropriateness(label, text, confidence)
        
        # 2. 명확성 (Clarity)
        scores["clarity"] = self._score_clarity(text)
        
        # 3. 맥락 일치 (Context Match)
        scores["context_match"] = self._score_context_match(label, text, agent_text)
        
        # 4. 응답 품질 (Response Quality)
        scores["response_quality"] = self._score_response_quality(label, text, confidence)
        
        return scores
    
    def _score_appropriateness(
        self,
        label: str,
        text: str,
        confidence: float
    ) -> float:
        """적절성 점수 (0-100)"""
        # 라벨과 텍스트의 적절성 평가
        # 신뢰도를 기반으로 점수 계산
        base_score = confidence * 100
        
        # 라벨별 가중치 조정
        label_weights = {
            NormalLabel.INQUIRY.value: 1.0,
            NormalLabel.COMPLAINT.value: 0.95,
            NormalLabel.REQUEST.value: 0.95,
            NormalLabel.CLARIFICATION.value: 0.9,
            NormalLabel.CONFIRMATION.value: 0.9,
            NormalLabel.CLOSING.value: 0.85
        }
        
        weight = label_weights.get(label, 0.9)
        return min(100.0, base_score * weight)
    
    def _score_clarity(self, text: str) -> float:
        """명확성 점수 (0-100)"""
        if not text:
            return 0.0
        
        # 텍스트 길이 기반 점수
        length = len(text.strip())
        
        if length < 5:
            return 50.0
        elif length < 20:
            return 70.0
        elif length < 100:
            return 85.0
        else:
            return 90.0
    
    def _score_context_match(
        self,
        label: str,
        text: str,
        agent_text: Optional[str] = None
    ) -> float:
        """맥락 일치 점수 (0-100)"""
        # 기본 점수
        base_score = 80.0
        
        # 상담사 응답이 있는 경우 맥락 일치 확인
        if agent_text:
            # 간단한 키워드 매칭 (향후 더 정교한 방법으로 개선 가능)
            text_keywords = set(text.lower().split())
            agent_keywords = set(agent_text.lower().split())
            
            if text_keywords & agent_keywords:
                base_score += 10.0
        
        return min(100.0, base_score)
    
    def _score_response_quality(
        self,
        label: str,
        text: str,
        confidence: float
    ) -> float:
        """응답 품질 점수 (0-100)"""
        # 신뢰도 기반 점수
        base_score = confidence * 100
        
        # 라벨별 품질 가중치
        quality_weights = {
            NormalLabel.INQUIRY.value: 0.95,
            NormalLabel.COMPLAINT.value: 0.9,
            NormalLabel.REQUEST.value: 0.95,
            NormalLabel.CLARIFICATION.value: 0.85,
            NormalLabel.CONFIRMATION.value: 0.9,
            NormalLabel.CLOSING.value: 0.9
        }
        
        weight = quality_weights.get(label, 0.9)
        return min(100.0, base_score * weight)
    
    def _generate_feedback(
        self,
        label: str,
        criteria_scores: Dict[str, float],
        total_score: float
    ) -> str:
        """
        피드백 생성
        
        Args:
            label: 라벨
            criteria_scores: 기준별 점수
            total_score: 전체 점수
        
        Returns:
            피드백 문자열
        """
        if total_score >= 85:
            return f"고객의 {label} 발화가 매우 명확하고 적절합니다."
        elif total_score >= 70:
            return f"고객의 {label} 발화가 적절하고 명확합니다."
        elif total_score >= 55:
            return f"고객의 {label} 발화가 부분적으로 적절합니다."
        else:
            return f"고객의 {label} 발화가 모호하거나 부적절할 수 있습니다."

