"""
발화 의도 예측 통합 인터페이스

Baseline 규칙 + KoSentenceBERT를 통합하여 발화 의도를 분류
"""

from typing import Optional, List
from datetime import datetime

from .baseline_rules import IntentBaselineRules
from ..data.data_structures import ClassificationResult
from ..config.labels import NORMAL_LABELS, SPECIAL_LABELS


class IntentPredictor:
    """발화 의도 예측기"""
    
    def __init__(self):
        """
        발화 의도 예측기 초기화
        """
        # KoSentenceBERT 분류기 (향후 구현)
        # from intent_classifier.kosentbert_classifier import KoSentenceBERTClassifier
        # self.classifier = KoSentenceBERTClassifier()
        self.classifier = None
        
        # Baseline 규칙은 모듈 내부에 포함
        self.baseline_rules = IntentBaselineRules()
    
    def predict(self, text: str, profanity_detected: bool, 
                session_context: Optional[List[str]] = None) -> ClassificationResult:
        """
        발화 의도 예측 (통합)
        
        Args:
            text: 분석할 문장
            profanity_detected: 1차 필터링에서 욕설 감지 여부
            session_context: 세션 맥락
        
        Returns:
            ClassificationResult (label, label_type, confidence, ...)
        """
        # 욕설 감지 시 즉시 특수 Label 반환
        if profanity_detected:
            return ClassificationResult(
                label="PROFANITY",
                label_type="SPECIAL",
                confidence=1.0,
                text=text,
                timestamp=datetime.now()
            )
        
        # Baseline 규칙으로 특수 Label 사전 감지
        baseline_results = self.baseline_rules.detect_special_labels(text, session_context)
        if baseline_results:
            # 가장 높은 신뢰도의 Label 선택
            label, confidence = max(baseline_results, key=lambda x: x[1])
            return ClassificationResult(
                label=label,
                label_type="SPECIAL",
                confidence=confidence,
                text=text,
                timestamp=datetime.now()
            )
        
        # KoSentenceBERT로 Normal Label 분류 (향후 구현)
        if self.classifier:
            intent_result = self.classifier.predict(text, session_context)
            label_type = self._determine_label_type(intent_result.label)
            
            return ClassificationResult(
                label=intent_result.label,
                label_type=label_type,
                confidence=intent_result.confidence,
                text=text,
                probabilities=intent_result.probabilities,
                timestamp=datetime.now()
            )
        
        # 모델이 없을 경우 기본값 (임시)
        # 실제 구현 시에는 모델이 필수
        return ClassificationResult(
            label="INQUIRY",  # 기본값
            label_type="NORMAL",
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
    
    def _determine_label_type(self, label: str) -> str:
        """
        Label 타입 결정 (Normal or Special)
        
        Args:
            label: 분류된 Label
        
        Returns:
            "NORMAL" or "SPECIAL"
        """
        if label in NORMAL_LABELS:
            return "NORMAL"
        elif label in SPECIAL_LABELS:
            return "SPECIAL"
        else:
            return "UNKNOWN"

