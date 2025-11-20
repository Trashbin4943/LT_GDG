"""
이벤트 생성

Special Label 감지 시 이벤트 생성
"""
from typing import Dict, Any, Optional
from datetime import datetime
from logic_classify_system.data.data_structures import SpecialLabelDetectionResult
import logging

logger = logging.getLogger(__name__)


class EventGenerator:
    """이벤트 생성기"""
    
    @staticmethod
    def generate_event(
        detection_result: SpecialLabelDetectionResult,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        이벤트 생성
        
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
        알림 이벤트 생성
        
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
