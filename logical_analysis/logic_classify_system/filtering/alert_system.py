"""
알림 시스템

Special Label 감지 시 알림 발송
"""
from typing import Optional, Dict, Any
from datetime import datetime
from logic_classify_system.data.data_structures import FilteringResult
import logging

logger = logging.getLogger(__name__)


class AlertSystem:
    """알림 시스템"""
    
    def __init__(self):
        """초기화"""
        self.alert_history = []
        self.alert_enabled = True
    
    def send_alert(
        self,
        filtering_result: FilteringResult,
        session_id: Optional[str] = None
    ) -> bool:
        """
        알림 발송
        
        Args:
            filtering_result: 필터링 결과
            session_id: 세션 ID
        
        Returns:
            발송 성공 여부
        """
        if not self.alert_enabled:
            return False
        
        alert = {
            "label": filtering_result.label,
            "severity": filtering_result.severity,
            "action": filtering_result.action,
            "alert_level": filtering_result.alert_level,
            "text": filtering_result.text,
            "timestamp": filtering_result.timestamp,
            "session_id": session_id
        }
        
        self.alert_history.append(alert)
        
        # 실제 알림 발송 로직 (예: 이메일, 슬랙, SMS 등)
        logger.warning(f"알림 발송: {filtering_result.label} ({filtering_result.severity}) - {filtering_result.action}")
        
        # 여기서 실제 알림 API 호출
        # 예: self._send_email(alert), self._send_slack(alert), etc.
        
        return True
    
    def get_alert_history(self, limit: int = 100) -> list:
        """
        알림 이력 조회
        
        Args:
            limit: 최대 조회 개수
        
        Returns:
            알림 이력 리스트
        """
        return self.alert_history[-limit:]
    
    def clear_history(self):
        """알림 이력 초기화"""
        self.alert_history = []
        logger.info("알림 이력 초기화됨")
