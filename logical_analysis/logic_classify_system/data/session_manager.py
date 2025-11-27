"""
세션 관리

대화 맥락을 저장하고 관리 (HEAD 기반)
세션별 대화 맥락 저장 및 조회 (logic 기능 통합)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """세션 매니저 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(self, max_history: int = 10, session_timeout_minutes: int = 30):
        """
        세션 매니저 초기화
        
        Args:
            max_history: 최대 저장할 발화 수 (logic: 추가)
            session_timeout_minutes: 세션 타임아웃 (분) (logic: 추가)
        """
        # HEAD: 간단한 구조 유지
        self.sessions: Dict[str, List[str]] = {}
        
        # logic: 추가 기능
        self.max_history = max_history
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.session_metadata: Dict[str, Dict] = {}  # logic: 세션 메타데이터
    
    def create_session(self, session_id: str):
        """
        세션 생성 (HEAD: 유지)
        
        Args:
            session_id: 세션 ID
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            # logic: 메타데이터 초기화
            self.session_metadata[session_id] = {
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
    
    def add_sentence(self, session_id: str, sentence: str):
        """
        문장 추가 (HEAD: 유지)
        
        Args:
            session_id: 세션 ID
            sentence: 추가할 문장
        """
        if session_id not in self.sessions:
            self.create_session(session_id)
        
        # HEAD: 기본 기능
        self.sessions[session_id].append(sentence)
        
        # logic: 최대 길이 제한
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]
        
        # logic: 메타데이터 업데이트
        if session_id in self.session_metadata:
            self.session_metadata[session_id]["last_updated"] = datetime.now()
    
    def get_context(self, session_id: str, window_size: int = 5) -> List[str]:
        """
        세션 맥락 반환 (최근 N개 문장) (HEAD: 유지)
        
        Args:
            session_id: 세션 ID
            window_size: 반환할 최근 문장 수
        
        Returns:
            최근 문장 리스트
        """
        if session_id not in self.sessions:
            return []
        
        # logic: 타임아웃 확인
        if session_id in self.session_metadata:
            session_meta = self.session_metadata[session_id]
            if self._is_session_expired(session_meta):
                self.clear_session(session_id)
                return []
        
        return self.sessions[session_id][-window_size:]
    
    def get_session_context(self, session_id: str) -> List[str]:
        """
        세션 맥락 조회 (logic: 추가 메서드)
        
        Args:
            session_id: 세션 ID
        
        Returns:
            발화 리스트 (최신 순)
        """
        return self.get_context(session_id, window_size=self.max_history)
    
    def add_to_session(self, session_id: str, text: str):
        """
        세션에 발화 추가 (logic: 추가 메서드, add_sentence와 동일)
        
        Args:
            session_id: 세션 ID
            text: 발화 텍스트
        """
        self.add_sentence(session_id, text)
    
    def clear_session(self, session_id: str):
        """
        세션 초기화 (HEAD: 유지)
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # logic: 메타데이터도 제거
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]
    
    def _is_session_expired(self, session_meta: Dict) -> bool:
        """세션 만료 여부 확인 (logic: 추가)"""
        last_updated = session_meta.get("last_updated")
        if last_updated is None:
            return True
        
        return datetime.now() - last_updated > self.session_timeout
    
    def _remove_session(self, session_id: str):
        """세션 제거 (logic: 추가)"""
        self.clear_session(session_id)
        logger.info(f"세션 만료로 제거됨: {session_id}")
    
    def cleanup_expired_sessions(self):
        """만료된 세션 정리 (logic: 추가)"""
        expired_sessions = [
            session_id for session_id, session_meta in self.session_metadata.items()
            if self._is_session_expired(session_meta)
        ]
        
        for session_id in expired_sessions:
            self._remove_session(session_id)
        
        if expired_sessions:
            logger.info(f"{len(expired_sessions)}개의 만료된 세션 정리됨")
