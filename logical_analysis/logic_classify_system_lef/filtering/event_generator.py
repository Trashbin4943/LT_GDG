"""
이벤트 생성

특수 Label에 따른 이벤트 생성 (HEAD 기반)
Special Label 감지 시 이벤트 생성 (logic 기능 통합)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from .baseline_rules import FilteringBaselineRules
from ..data.data_structures import SpecialLabelDetectionResult

logger = logging.getLogger(__name__)


@dataclass
class FilteringEvent:
    """필터링 이벤트 (HEAD: 유지)"""
    label: str
    severity: str
    action: str
    alert_level: str
    text: str
    session_context: Optional[List[str]]
    timestamp: datetime
    config: Dict[str, Any]  # 추가 설정 정보


class EventGenerator:
    """이벤트 생성기 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(self):
        """
        이벤트 생성기 초기화 (HEAD: 유지)
        """
        # Baseline 규칙은 모듈 내부에 포함
        self.baseline_rules = FilteringBaselineRules()
    
    def generate(
        self,
        label: Optional[str] = None,
        severity: Optional[str] = None,
        text: Optional[str] = None,
        session_context: Optional[List[str]] = None,
        detection_result: Optional[SpecialLabelDetectionResult] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FilteringEvent:
        """
        이벤트 생성 (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            label: 특수 Label (HEAD 방식)
            severity: 심각도 (HEAD 방식)
            text: 발화 텍스트 (HEAD 방식)
            session_context: 세션 맥락 (HEAD 방식)
            detection_result: 감지 결과 (logic 방식)
            session_id: 세션 ID (logic 방식)
            metadata: 추가 메타데이터 (logic 방식)
        
        Returns:
            FilteringEvent
        """
        # logic 방식 지원
        if detection_result:
            label = detection_result.label
            severity = detection_result.severity
            text = detection_result.text or ""
            session_context = None
        
        # HEAD 방식: 필수 파라미터 확인
        if not label or not severity or not text:
            raise ValueError("label, severity, text 또는 detection_result가 필요합니다.")
        
        # Label별 이벤트 설정 (모듈 내부 규칙 사용)
        event_config = self.baseline_rules.get_event_config(label)
        
        # logic: metadata 통합
        if metadata:
            event_config.update(metadata)
        
        return FilteringEvent(
            label=label,
            severity=severity,
            action=event_config.get("action", "MONITOR"),
            alert_level=event_config.get("alert_level", "MEDIUM"),
            text=text,
            session_context=session_context,
            timestamp=datetime.now(),
            config=event_config
        )
    
    @staticmethod
    def generate_event(
        detection_result: SpecialLabelDetectionResult,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        이벤트 생성 (logic: 추가 메서드, Dict 반환)
        
        Args:
            detection_result: 감지 결과
            session_id: 세션 ID
            metadata: 추가 메타데이터
        
        Returns:
            이벤트 딕셔너리
        """
        event = {
            "event_type": "SPECIAL_LABEL_DETECTED",
            "label": detection_result.label,
            "severity": detection_result.severity,
            "confidence": detection_result.confidence,
            "detection_method": detection_result.detection_method,
            "text": detection_result.text,
            "timestamp": detection_result.timestamp or datetime.now(),
            "session_id": session_id
        }
        
        if metadata:
            event["metadata"] = metadata
        
        logger.info(f"이벤트 생성: {event['event_type']} - {event['label']} ({event['severity']})")
        
        return event
    
    @staticmethod
    def generate_alert_event(
        label: str,
        severity: str,
        text: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        알림 이벤트 생성 (logic: 추가)
        
        Args:
            label: 라벨
            severity: 심각도
            text: 텍스트
            session_id: 세션 ID
        
        Returns:
            알림 이벤트 딕셔너리
        """
        event = {
            "event_type": "ALERT",
            "label": label,
            "severity": severity,
            "text": text,
            "timestamp": datetime.now(),
            "session_id": session_id
        }
        
        logger.warning(f"알림 이벤트 생성: {label} ({severity})")
        
        return event
