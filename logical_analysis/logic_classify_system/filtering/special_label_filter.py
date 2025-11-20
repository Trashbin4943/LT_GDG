"""
Special Label 필터

Special Label 감지 및 필터링 (AI-Hub 모델 + Baseline 규칙)
"""
from typing import Optional, List
from datetime import datetime
from logic_classify_system.data.data_structures import (
    SpecialLabelDetectionResult,
    FilteringResult
)
from logic_classify_system.filtering.aihub_special_label_detector import AIHubSpecialLabelDetector
from logic_classify_system.filtering.baseline_rules import FilteringBaselineRules
from logic_classify_system.intent_classifier.baseline_rules import IntentBaselineRules
from logic_classify_system.filtering.event_generator import EventGenerator
from logic_classify_system.filtering.alert_system import AlertSystem
from logic_classify_system.config.labels import SpecialLabel
import logging

logger = logging.getLogger(__name__)


class SpecialLabelFilter:
    """Special Label 필터"""
    
    # 심각도 → 액션 매핑
    SEVERITY_ACTION_MAPPING = {
        "HIGH": "ALERT",
        "MEDIUM": "LOG",
        "LOW": "LOG"
    }
    
    def __init__(self, aihub_detector: Optional[AIHubSpecialLabelDetector] = None):
        """
        초기화
        
        Args:
            aihub_detector: AIHubSpecialLabelDetector 인스턴스
        """
        self.aihub_detector = aihub_detector
        self.filtering_baseline = FilteringBaselineRules()
        self.intent_baseline = IntentBaselineRules()
        self.event_generator = EventGenerator()
        self.alert_system = AlertSystem()
    
    def detect(
        self,
        text: str,
        session_context: Optional[List[str]] = None
    ) -> Optional[SpecialLabelDetectionResult]:
        """
        Special Label 감지 (AI-Hub 모델 우선, Baseline 규칙 폴백)
        
        Args:
            text: 분석할 텍스트
            session_context: 세션 맥락
        
        Returns:
            SpecialLabelDetectionResult 또는 None (감지 실패 시)
        """
        # 1. AI-Hub 모델 감지 (우선순위 1)
        if self.aihub_detector:
            result = self.aihub_detector.detect(text, session_context)
            if result:
                return result
        
        # 2. Baseline 규칙 감지 (우선순위 2)
        # IntentBaselineRules를 사용하여 UNREASONABLE_DEMAND, REPETITION 감지
        baseline_result = self.intent_baseline.detect_special_labels(text, session_context)
        
        if baseline_result and baseline_result.label_type == "SPECIAL":
            # SpecialLabelDetectionResult로 변환
            return SpecialLabelDetectionResult(
                label=baseline_result.label,
                confidence=baseline_result.confidence,
                severity=self._calculate_severity(baseline_result.label),
                detection_method="baseline",
                text=text,
                timestamp=datetime.now()
            )
        
        return None
    
    def filter(
        self,
        detection_result: SpecialLabelDetectionResult,
        session_id: Optional[str] = None
    ) -> FilteringResult:
        """
        필터링 수행 (심각도 확인, 이벤트 생성, 알림 발송)
        
        Args:
            detection_result: 감지 결과
            session_id: 세션 ID
        
        Returns:
            FilteringResult
        """
        # 심각도 확인
        severity = detection_result.severity
        
        # 액션 결정
        action = self.SEVERITY_ACTION_MAPPING.get(severity, "LOG")
        
        # 필터링 결과 생성
        filtering_result = FilteringResult(
            label=detection_result.label,
            severity=severity,
            action=action,
            alert_level=severity,
            text=detection_result.text or "",
            timestamp=detection_result.timestamp or datetime.now()
        )
        
        # 이벤트 생성
        event = self.event_generator.generate_event(
            detection_result,
            session_id=session_id
        )
        
        # 알림 발송 (HIGH 심각도 또는 ALERT 액션인 경우)
        if action == "ALERT" or severity == "HIGH":
            self.alert_system.send_alert(filtering_result, session_id=session_id)
        
        return filtering_result
    
    @staticmethod
    def _calculate_severity(label: str) -> str:
        """라벨에 따른 심각도 계산"""
        severity_mapping = {
            SpecialLabel.VIOLENCE_THREAT.value: "HIGH",
            SpecialLabel.SEXUAL_HARASSMENT.value: "HIGH",
            SpecialLabel.HATE_SPEECH.value: "HIGH",
            SpecialLabel.PROFANITY.value: "MEDIUM",
            SpecialLabel.UNREASONABLE_DEMAND.value: "MEDIUM",
            SpecialLabel.REPETITION.value: "LOW"
        }
        return severity_mapping.get(label, "MEDIUM")
