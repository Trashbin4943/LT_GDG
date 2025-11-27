"""
알림 시스템

경고, 통화 중단 등의 알림 발송 (HEAD 기반)
Special Label 감지 시 알림 발송 (logic 기능 통합)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .event_generator import FilteringEvent
from ..data.data_structures import FilteringResult

logger = logging.getLogger(__name__)


class AlertSystem:
    """알림 시스템 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(self):
        """
        알림 시스템 초기화
        """
        # HEAD: FilteringEvent 리스트
        self.alert_history: List[FilteringEvent] = []
        # logic: alert_enabled 플래그
        self.alert_enabled = True
    
    def send_alert(
        self,
        event: Optional[FilteringEvent] = None,
        filtering_result: Optional[FilteringResult] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        알림 발송 (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            event: 필터링 이벤트 (HEAD 방식)
            filtering_result: 필터링 결과 (logic 방식)
            session_id: 세션 ID (logic 방식)
        
        Returns:
            발송 성공 여부 (logic 방식) 또는 None (HEAD 방식)
        """
        if not self.alert_enabled:
            return False
        
        # HEAD 방식
        if event:
            self.alert_history.append(event)
            
            if event.alert_level == "CRITICAL":
                self._send_critical_alert(event)
            elif event.alert_level == "HIGH":
                self._send_high_alert(event)
            elif event.alert_level == "MEDIUM":
                self._send_medium_alert(event)
            else:
                self._send_low_alert(event)
            return True
        
        # logic 방식
        elif filtering_result:
            alert = {
                "label": filtering_result.label,
                "severity": filtering_result.severity,
                "action": filtering_result.action,
                "alert_level": filtering_result.alert_level,
                "text": filtering_result.text,
                "timestamp": filtering_result.timestamp,
                "session_id": session_id
            }
            
            # FilteringEvent로 변환하여 저장
            try:
                filtering_event = FilteringEvent(
                    label=filtering_result.label,
                    severity=filtering_result.severity,
                    action=filtering_result.action,
                    alert_level=filtering_result.alert_level,
                    text=filtering_result.text,
                    session_context=None,
                    timestamp=filtering_result.timestamp,
                    config={"session_id": session_id} if session_id else {}
                )
                self.alert_history.append(filtering_event)
            except Exception as e:
                logger.warning(f"FilteringEvent 변환 실패: {e}")
            
            logger.warning(f"알림 발송: {filtering_result.label} ({filtering_result.severity}) - {filtering_result.action}")
            return True
        
        return False
    
    def _send_critical_alert(self, event: FilteringEvent):
        """CRITICAL 알림 발송 (즉시 통화 중단) (HEAD: 유지)"""
        print(f"[CRITICAL ALERT] {event.label} 감지")
        print(f"  텍스트: {event.text}")
        print(f"  조치: {event.action}")
        print(f"  심각도: {event.severity}")
        
        if event.config.get("recording", False):
            print("  → 녹음 보관 필요")
        
        if event.config.get("legal_review", False):
            print("  → 법적 검토 필요")
    
    def _send_high_alert(self, event: FilteringEvent):
        """HIGH 알림 발송 (경고) (HEAD: 유지)"""
        print(f"[HIGH ALERT] {event.label} 감지")
        print(f"  텍스트: {event.text}")
        print(f"  조치: {event.action}")
        
        if event.config.get("terminate_on_repeat", False):
            print("  → 반복 시 통화 중단 경고")
    
    def _send_medium_alert(self, event: FilteringEvent):
        """MEDIUM 알림 발송 (상담사 지원) (HEAD: 유지)"""
        print(f"[MEDIUM ALERT] {event.label} 감지")
        print(f"  텍스트: {event.text}")
        print(f"  조치: {event.action}")
        
        if event.config.get("provide_guidance", False):
            print("  → 상담사 지원 가이드 제공")
        
        if event.config.get("provide_strategy", False):
            print("  → 대화 전환 전략 제시")
    
    def _send_low_alert(self, event: FilteringEvent):
        """LOW 알림 발송 (모니터링) (HEAD: 유지)"""
        print(f"[LOW ALERT] {event.label} 감지")
        print(f"  텍스트: {event.text}")
        print(f"  조치: 모니터링")
    
    def get_alert_history(self, limit: int = 100) -> list:
        """
        알림 이력 조회 (logic: 추가)
        
        Args:
            limit: 최대 조회 개수
        
        Returns:
            알림 이력 리스트
        """
        return self.alert_history[-limit:]
    
    def clear_history(self):
        """알림 이력 초기화 (logic: 추가)"""
        self.alert_history = []
        logger.info("알림 이력 초기화됨")
