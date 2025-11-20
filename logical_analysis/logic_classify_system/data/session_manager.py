"""
세션 관리

세션별 대화 맥락 저장 및 조회
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """세션별 대화 맥락 관리"""
    
    def __init__(self, max_history: int = 10, session_timeout_minutes: int = 30):
        """
        초기화
        
        Args:
            max_history: 최대 저장할 발화 수
            session_timeout_minutes: 세션 타임아웃 (분)
        """
        self.sessions: Dict[str, Dict] = {}
        self.max_history = max_history
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
    
    def get_session_context(self, session_id: str) -> List[str]:
        """
        세션 맥락 조회
        
        Args:
            session_id: 세션 ID
        
        Returns:
            발화 리스트 (최신 순)
        """
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        
        # 타임아웃 확인
        if self._is_session_expired(session):
            self._remove_session(session_id)
            return []
        
        return session.get("context", [])
    
    def add_to_session(self, session_id: str, text: str):
        """
        세션에 발화 추가
        
        Args:
            session_id: 세션 ID
            text: 발화 텍스트
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "context": [],
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
        
        session = self.sessions[session_id]
        
        # 타임아웃 확인
        if self._is_session_expired(session):
            # 세션 재생성
            self.sessions[session_id] = {
                "context": [],
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            session = self.sessions[session_id]
        
        # 맥락에 추가
        context = session["context"]
        context.append(text)
        
        # 최대 길이 제한
        if len(context) > self.max_history:
            context = context[-self.max_history:]
        
        session["context"] = context
        session["last_updated"] = datetime.now()
    
    def clear_session(self, session_id: str):
        """
        세션 초기화
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def _is_session_expired(self, session: Dict) -> bool:
        """세션 만료 여부 확인"""
        last_updated = session.get("last_updated")
        if last_updated is None:
            return True
        
        return datetime.now() - last_updated > self.session_timeout
    
    def _remove_session(self, session_id: str):
        """세션 제거"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"세션 만료로 제거됨: {session_id}")
    
    def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if self._is_session_expired(session)
        ]
        
        for session_id in expired_sessions:
            self._remove_session(session_id)
        
        if expired_sessions:
            logger.info(f"{len(expired_sessions)}개의 만료된 세션 정리됨")
