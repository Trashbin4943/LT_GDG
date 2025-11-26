"""
STT 출력 전처리기

emotion_system의 STT 출력을 Turn 단위로 변환하고
CustomerAnalysisResult 생성을 위한 전처리 수행
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class STTSegment:
    """STT 세그먼트 (원본 STT 출력 구조)"""
    speaker: str  # "SPEAKER_00", "SPEAKER_01" 등
    start: float  # 시작 시간 (초)
    end: float  # 종료 시간 (초)
    text: str  # 텍스트


@dataclass
class Turn:
    """발화 Turn (손님-상담원 쌍)"""
    turn_index: int
    customer_text: str  # 손님 발화 (해당 Turn의 손님 발화만)
    agent_text: Optional[str] = None  # 상담원 발화 (해당 Turn의 상담원 발화만)
    customer_timestamp: Optional[datetime] = None  # 손님 발화 시작 시간
    agent_timestamp: Optional[datetime] = None  # 상담원 발화 시작 시간
    
    @property
    def session_timestamp(self) -> Optional[datetime]:
        """세션 타임스탬프 (손님 발화 시간 우선)"""
        return self.customer_timestamp or self.agent_timestamp


class STTPreprocessor:
    """STT 출력 전처리기"""
    
    def __init__(self, customer_speaker: Optional[str] = None):
        """
        STT 전처리기 초기화
        
        Args:
            customer_speaker: 손님 화자 라벨 (예: "SPEAKER_00")
                            None이면 자동으로 첫 번째 화자를 손님으로 간주
        """
        self.customer_speaker = customer_speaker
        self.agent_speaker = None  # 손님 화자가 정해지면 나머지가 상담원
    
    def _identify_speakers(self, segments: List[STTSegment]) -> tuple[str, Optional[str]]:
        """
        세그먼트에서 손님/상담원 화자 자동 식별
        
        Args:
            segments: STT 세그먼트 리스트
            
        Returns:
            (customer_speaker, agent_speaker) 튜플
        """
        if not segments:
            return "SPEAKER_00", None
        
        # 사용자가 지정한 손님 화자가 있으면 그대로 사용
        if self.customer_speaker:
            speakers = {seg.speaker for seg in segments}
            agent = next((s for s in speakers if s != self.customer_speaker), None)
            return self.customer_speaker, agent
        
        # 자동 식별: 첫 번째 발화 화자를 손님으로 간주
        first_speaker = segments[0].speaker
        speakers = {seg.speaker for seg in segments}
        agent = next((s for s in speakers if s != first_speaker), None)
        
        return first_speaker, agent
    
    def parse_stt_output(self, stt_data: List[Dict[str, Any]]) -> List[STTSegment]:
        """
        STT 원본 출력을 STTSegment 리스트로 파싱
        
        Args:
            stt_data: STT 원본 출력
                     형식: [
                         {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.5, "text": "안녕하세요"},
                         ...
                     ]
        
        Returns:
            STTSegment 리스트
        """
        segments = []
        for item in stt_data:
            segment = STTSegment(
                speaker=item.get("speaker", ""),
                start=float(item.get("start", 0.0)),
                end=float(item.get("end", 0.0)),
                text=item.get("text", "").strip()
            )
            if segment.text:  # 빈 텍스트는 제외
                segments.append(segment)
        
        return segments
    
    def parse_speaker_segments(self, speaker_segments) -> List[STTSegment]:
        """
        Django SpeakerSegment 모델 쿼리셋을 STTSegment 리스트로 변환
        
        Args:
            speaker_segments: SpeakerSegment 모델 쿼리셋 또는 리스트
        
        Returns:
            STTSegment 리스트
        """
        segments = []
        for seg in speaker_segments:
            # Django 모델 또는 딕셔너리 모두 처리
            if hasattr(seg, 'speaker_label'):
                segment = STTSegment(
                    speaker=seg.speaker_label,
                    start=float(seg.start_time),
                    end=float(seg.end_time),
                    text=seg.text.strip()
                )
            else:
                segment = STTSegment(
                    speaker=seg.get("speaker_label", ""),
                    start=float(seg.get("start_time", 0.0)),
                    end=float(seg.get("end_time", 0.0)),
                    text=seg.get("text", "").strip()
                )
            
            if segment.text:  # 빈 텍스트는 제외
                segments.append(segment)
        
        return segments
    
    def split_into_turns(self, segments: List[STTSegment]) -> List[Turn]:
        """
        STT 세그먼트를 Turn 단위로 분할
        
        Args:
            segments: STTSegment 리스트
        
        Returns:
            Turn 리스트
        """
        if not segments:
            return []
        
        # 화자 식별
        customer_speaker, agent_speaker = self._identify_speakers(segments)
        
        turns = []
        current_customer_texts = []  # 현재 Turn의 손님 발화들
        current_agent_texts = []  # 현재 Turn의 상담원 발화들
        current_customer_start = None
        current_agent_start = None
        turn_index = 0
        
        for segment in segments:
            # 손님 발화인 경우
            if segment.speaker == customer_speaker:
                # 이전 Turn이 완성되어 있으면 저장
                if current_customer_texts:
                    turn = Turn(
                        turn_index=turn_index,
                        customer_text=" ".join(current_customer_texts),
                        agent_text=" ".join(current_agent_texts) if current_agent_texts else None,
                        customer_timestamp=self._float_to_datetime(current_customer_start),
                        agent_timestamp=self._float_to_datetime(current_agent_start) if current_agent_start else None
                    )
                    turns.append(turn)
                    turn_index += 1
                
                # 새로운 Turn 시작
                current_customer_texts = [segment.text]
                current_agent_texts = []
                current_customer_start = segment.start
                current_agent_start = None
            
            # 상담원 발화인 경우
            elif segment.speaker == agent_speaker:
                # 현재 Turn에 추가
                current_agent_texts.append(segment.text)
                if current_agent_start is None:
                    current_agent_start = segment.start
        
        # 마지막 Turn 저장
        if current_customer_texts:
            turn = Turn(
                turn_index=turn_index,
                customer_text=" ".join(current_customer_texts),
                agent_text=" ".join(current_agent_texts) if current_agent_texts else None,
                customer_timestamp=self._float_to_datetime(current_customer_start),
                agent_timestamp=self._float_to_datetime(current_agent_start) if current_agent_start else None
            )
            turns.append(turn)
        
        return turns
    
    def _float_to_datetime(self, timestamp_float: Optional[float]) -> Optional[datetime]:
        """
        float 타임스탬프를 datetime으로 변환
        
        Args:
            timestamp_float: 초 단위 타임스탬프
        
        Returns:
            datetime 객체 또는 None
        """
        if timestamp_float is None:
            return None
        
        # 오늘 날짜 기준으로 시간을 계산 (실제로는 세션 시작 시간을 사용해야 함)
        # 현재는 기본값으로 처리
        try:
            base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return base_date.replace(
                hour=int(timestamp_float // 3600),
                minute=int((timestamp_float % 3600) // 60),
                second=int(timestamp_float % 60),
                microsecond=int((timestamp_float % 1) * 1000000)
            )
        except Exception:
            return datetime.now()  # 변환 실패 시 현재 시간 반환
    
    def process(self, stt_input: Any, session_id: str, session_start_time: Optional[datetime] = None) -> List[Turn]:
        """
        STT 입력을 처리하여 Turn 리스트 반환 (통합 메서드)
        
        Args:
            stt_input: STT 입력 데이터
                      - List[Dict]: STT 원본 출력
                      - SpeakerSegment 쿼리셋: Django 모델 쿼리셋
                      - List[STTSegment]: 이미 파싱된 세그먼트 리스트
            session_id: 세션 ID
            session_start_time: 세션 시작 시간 (타임스탬프 계산용)
        
        Returns:
            Turn 리스트
        """
        # 입력 타입에 따라 처리
        if isinstance(stt_input, list):
            if stt_input and isinstance(stt_input[0], dict):
                # STT 원본 출력 형식
                segments = self.parse_stt_output(stt_input)
            elif stt_input and isinstance(stt_input[0], STTSegment):
                # 이미 파싱된 세그먼트
                segments = stt_input
            else:
                # Django 모델 리스트
                segments = self.parse_speaker_segments(stt_input)
        else:
            # Django 모델 쿼리셋
            segments = self.parse_speaker_segments(stt_input)
        
        # Turn 단위로 분할
        turns = self.split_into_turns(segments)
        
        # session_start_time이 있으면 타임스탬프 보정
        if session_start_time and turns:
            for turn in turns:
                if turn.customer_timestamp:
                    # 상대 시간을 절대 시간으로 변환
                    relative_seconds = (
                        turn.customer_timestamp.hour * 3600 +
                        turn.customer_timestamp.minute * 60 +
                        turn.customer_timestamp.second +
                        turn.customer_timestamp.microsecond / 1000000
                    )
                    turn.customer_timestamp = session_start_time.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    from datetime import timedelta
                    turn.customer_timestamp += timedelta(seconds=relative_seconds)
        
        return turns

