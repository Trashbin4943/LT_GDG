"""
Intent Baseline 규칙

UNREASONABLE_DEMAND, REPETITION 감지
"""
from typing import Optional, List
from logic_classify_system.data.data_structures import ClassificationResult
from logic_classify_system.config.labels import SpecialLabel, LabelType
import logging

logger = logging.getLogger(__name__)


class IntentBaselineRules:
    """Intent Baseline 규칙"""
    
    # 무리한 요구 키워드
    UNREASONABLE_DEMAND_KEYWORDS = [
        "지금 당장", "바로", "즉시", "지금", "당장", "금방",
        "지금 해줘", "바로 해줘", "당장 해줘"
    ]
    
    # 강요 표현
    PRESSURE_KEYWORDS = [
        "해야 해", "해야 한다", "안 되면", "안 하면", "시발",
        "화나게 하지 마", "빨리", "급하다"
    ]
    
    @classmethod
    def detect_special_labels(
        cls,
        text: str,
        session_context: Optional[List[str]] = None
    ) -> Optional[ClassificationResult]:
        """
        Special Label 감지 (UNREASONABLE_DEMAND, REPETITION)
        
        Args:
            text: 분석할 텍스트
            session_context: 세션 맥락 (반복 감지용)
        
        Returns:
            ClassificationResult 또는 None
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # 무리한 요구 감지
        unreasonable_detected = False
        for keyword in cls.UNREASONABLE_DEMAND_KEYWORDS:
            if keyword in text_lower:
                unreasonable_detected = True
                break
        
        if unreasonable_detected:
            # 강요 표현 확인
            has_pressure = any(keyword in text_lower for keyword in cls.PRESSURE_KEYWORDS)
            confidence = 0.90 if has_pressure else 0.75
            
            return ClassificationResult(
                label=SpecialLabel.UNREASONABLE_DEMAND.value,
                label_type=LabelType.SPECIAL.value,
                confidence=confidence,
                text=text
            )
        
        # 반복 감지
        if session_context and len(session_context) >= 2:
            # 최근 3개 발화 중 유사한 발화 확인
            recent_context = session_context[-3:]
            text_normalized = text.strip().lower()
            
            for ctx_text in recent_context:
                ctx_normalized = ctx_text.strip().lower()
                # 유사도 간단 계산 (같은 문장이면 반복)
                if text_normalized == ctx_normalized:
                    return ClassificationResult(
                        label=SpecialLabel.REPETITION.value,
                        label_type=LabelType.SPECIAL.value,
                        confidence=0.85,
                        text=text
                    )
                
                # 부분 일치 확인 (70% 이상 유사)
                similarity = cls._calculate_similarity(text_normalized, ctx_normalized)
                if similarity > 0.7:
                    return ClassificationResult(
                        label=SpecialLabel.REPETITION.value,
                        label_type=LabelType.SPECIAL.value,
                        confidence=0.75,
                        text=text
                    )
        
        return None
    
    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """간단한 유사도 계산 (Levenshtein 기반)"""
        if not text1 or not text2:
            return 0.0
        
        # 간단한 Jaccard 유사도
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
