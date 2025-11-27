"""
종합 필터링용 Baseline 규칙

특수 Label의 심각도 판단 및 이벤트 생성에 사용 (HEAD 기반)
Filtering Baseline 규칙 (logic 기능 통합)
"""

from typing import Dict, Optional
import logging

from ..data.data_structures import SpecialLabelDetectionResult
from ..config.labels import SpecialLabel

logger = logging.getLogger(__name__)


class FilteringBaselineRules:
    """종합 필터링용 Baseline 규칙 (HEAD 기반 + logic 기능 통합)"""
    
    # 심각도별 Label 매핑 (HEAD: 유지)
    SEVERITY_MAP: Dict[str, list] = {
        "CRITICAL": ["VIOLENCE_THREAT", "SEXUAL_HARASSMENT"],
        "HIGH": ["PROFANITY", "HATE_SPEECH"],
        "MEDIUM": ["UNREASONABLE_DEMAND", "REPETITION"]
    }
    
    # Label별 이벤트 설정 (HEAD: 유지)
    EVENT_CONFIG: Dict[str, Dict[str, any]] = {
        "VIOLENCE_THREAT": {
            "action": "TERMINATE_CALL",
            "alert_level": "CRITICAL",
            "recording": True,
            "legal_review": True
        },
        "SEXUAL_HARASSMENT": {
            "action": "TERMINATE_CALL",
            "alert_level": "CRITICAL",
            "recording": True,
            "legal_review": True
        },
        "PROFANITY": {
            "action": "WARN",
            "alert_level": "HIGH",
            "terminate_on_repeat": True
        },
        "HATE_SPEECH": {
            "action": "WARN",
            "alert_level": "HIGH",
            "terminate_on_repeat": True
        },
        "UNREASONABLE_DEMAND": {
            "action": "SUPPORT_AGENT",
            "alert_level": "MEDIUM",
            "provide_guidance": True
        },
        "REPETITION": {
            "action": "SUPPORT_AGENT",
            "alert_level": "MEDIUM",
            "provide_strategy": True
        }
    }
    
    @staticmethod
    def get_severity(label: str) -> str:
        """
        Label별 심각도 반환 (HEAD: 유지)
        
        Args:
            label: 특수 Label
        
        Returns:
            심각도 (CRITICAL, HIGH, MEDIUM)
        """
        for severity, labels in FilteringBaselineRules.SEVERITY_MAP.items():
            if label in labels:
                return severity
        return "MEDIUM"
    
    @staticmethod
    def get_event_config(label: str) -> Dict[str, any]:
        """
        Label별 이벤트 설정 반환 (HEAD: 유지)
        
        Args:
            label: 특수 Label
        
        Returns:
            이벤트 설정 딕셔너리
        """
        return FilteringBaselineRules.EVENT_CONFIG.get(label, {
            "action": "MONITOR",
            "alert_level": "MEDIUM"
        })
    
    @classmethod
    def detect(cls, text: str) -> Optional[SpecialLabelDetectionResult]:
        """
        Baseline 규칙으로 Special Label 감지 (logic: 추가)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            SpecialLabelDetectionResult 또는 None
        """
        # Intent Baseline Rules와 중복될 수 있으므로,
        # 여기서는 필터링 전용 규칙만 구현
        # (대부분의 Baseline 규칙은 IntentBaselineRules에서 처리)
        
        return None
