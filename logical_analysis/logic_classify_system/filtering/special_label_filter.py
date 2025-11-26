"""
특수 Label 종합 필터링

특수 Label에 대한 종합 필터링 및 이벤트 생성 (HEAD 기반)
Special Label 감지 및 필터링 (AI-Hub 모델 + Baseline 규칙) (logic 기능 통합)
"""

from typing import Optional, List
from datetime import datetime
import logging

from .baseline_rules import FilteringBaselineRules
from .event_generator import EventGenerator
from .alert_system import AlertSystem
from ..data.data_structures import (
    SpecialLabelDetectionResult,
    FilteringResult
)
from ..config.labels import SpecialLabel

logger = logging.getLogger(__name__)


class SpecialLabelFilter:
    """특수 Label 필터 (HEAD 기반 + logic 기능 통합)"""
    
    # 심각도 → 액션 매핑 (logic: 추가)
    SEVERITY_ACTION_MAPPING = {
        "HIGH": "ALERT",
        "MEDIUM": "LOG",
        "LOW": "LOG"
    }
    
    def __init__(self, aihub_detector: Optional[Any] = None):
        """
        특수 Label 필터 초기화
        
        Args:
            aihub_detector: AIHubSpecialLabelDetector 인스턴스 (logic: 추가)
        """
        # HEAD: 기본 구조 유지
        self.baseline_rules = FilteringBaselineRules()
        self.event_generator = EventGenerator()
        self.alert_system = AlertSystem()
        
        # logic: AIHub detector 추가
        try:
            from .aihub_special_label_detector import AIHubSpecialLabelDetector
            self.aihub_detector = aihub_detector or None
        except ImportError:
            self.aihub_detector = None
    
    def filter(
        self,
        label: Optional[str] = None,
        text: Optional[str] = None,
        session_context: Optional[List[str]] = None,
        detection_result: Optional[SpecialLabelDetectionResult] = None,
        session_id: Optional[str] = None
    ) -> FilteringResult:
        """
        특수 Label 필터링 (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            label: 특수 Label (HEAD 방식)
            text: 발화 텍스트 (HEAD 방식)
            session_context: 세션 맥락 (HEAD 방식)
            detection_result: 감지 결과 (logic 방식)
            session_id: 세션 ID (logic 방식)
        
        Returns:
            FilteringResult
        """
        # logic 방식 지원
        if detection_result:
            label = detection_result.label
            text = detection_result.text or ""
            severity = detection_result.severity
            
            # 액션 결정 (logic 방식)
            action = self.SEVERITY_ACTION_MAPPING.get(severity, "LOG")
            
            # 필터링 결과 생성
            filtering_result = FilteringResult(
                label=label,
                severity=severity,
                action=action,
                alert_level=severity,
                text=text,
                timestamp=detection_result.timestamp or datetime.now(),
                metadata=None
            )
            
            # 이벤트 생성 (logic 방식)
            event_dict = self.event_generator.generate_event(
                detection_result,
                session_id=session_id
            )
            
            # 알림 발송 (HIGH 심각도 또는 ALERT 액션인 경우)
            if action == "ALERT" or severity == "HIGH":
                self.alert_system.send_alert(
                    filtering_result=filtering_result,
                    session_id=session_id
                )
            
            return filtering_result
        
        # HEAD 방식: 필수 파라미터 확인
        if not label or not text:
            raise ValueError("label, text 또는 detection_result가 필요합니다.")
        
        # Label별 심각도 확인 (모듈 내부 규칙 사용)
        severity = self.baseline_rules.get_severity(label)
        
        # 이벤트 생성
        event = self.event_generator.generate(label, severity, text, session_context)
        
        # 알림 발송
        self.alert_system.send_alert(event)
        
        return FilteringResult(
            label=label,
            severity=severity,
            action=event.action,
            alert_level=event.alert_level,
            text=text,
            timestamp=datetime.now(),
            metadata=None
        )
    
    def detect(
        self,
        text: str,
        session_context: Optional[List[str]] = None
    ) -> Optional[SpecialLabelDetectionResult]:
        """
        Special Label 감지 (AI-Hub 모델 우선, Baseline 규칙 폴백) (logic: 추가)
        
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
        from ..intent_classifier.baseline_rules import IntentBaselineRules
        intent_baseline = IntentBaselineRules()
        baseline_results = intent_baseline.detect_special_labels(text, session_context)
        
        if baseline_results:
            # List[Tuple] 또는 ClassificationResult 처리
            if isinstance(baseline_results, list) and len(baseline_results) > 0:
                # HEAD 방식: List[Tuple[str, float]]
                label, confidence = max(baseline_results, key=lambda x: x[1])
            else:
                # logic 방식: ClassificationResult
                baseline_result = baseline_results
                label = baseline_result.label
                confidence = baseline_result.confidence
            
            # SpecialLabelDetectionResult로 변환
            return SpecialLabelDetectionResult(
                label=label,
                confidence=confidence,
                severity=self._calculate_severity(label),
                detection_method="baseline",
                text=text,
                timestamp=datetime.now()
            )
        
        return None
    
    @staticmethod
    def _calculate_severity(label: str) -> str:
        """라벨에 따른 심각도 계산 (logic: 추가)"""
        severity_mapping = {
            SpecialLabel.VIOLENCE_THREAT.value: "HIGH",
            SpecialLabel.SEXUAL_HARASSMENT.value: "HIGH",
            SpecialLabel.HATE_SPEECH.value: "HIGH",
            SpecialLabel.PROFANITY.value: "MEDIUM",
            SpecialLabel.UNREASONABLE_DEMAND.value: "MEDIUM",
            SpecialLabel.REPETITION.value: "LOW"
        }
        return severity_mapping.get(label, "MEDIUM")
