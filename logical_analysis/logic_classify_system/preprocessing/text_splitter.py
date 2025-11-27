"""
Turn 단위 텍스트 분할

STT 결과에서 Turn 단위로 텍스트를 분할
"""

from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Turn:
    """발화 Turn"""
    turn_index: int
    customer_text: str  # 손님 발화
    agent_text: Optional[str] = None  # 상담원 발화 (있는 경우)
    timestamp: Optional[Any] = None  # 타임스탬프 (선택사항)


class TurnSplitter:
    """Turn 단위 텍스트 분할기"""
    
    def __init__(self):
        """Turn 분할기 초기화"""
        pass
    
    def split_into_turns(self, stt_data: Dict[str, Any]) -> List[Turn]:
        """
        STT 결과를 Turn 단위로 분할
        
        Args:
            stt_data: STT 결과 딕셔너리
                예: {
                    "session_id": "session_001",
                    "segments": [
                        {"speaker": "customer", "text": "안녕하세요", "timestamp": ...},
                        {"speaker": "agent", "text": "네 안녕하세요", "timestamp": ...},
                        ...
                    ]
                }
        
        Returns:
            Turn 리스트
        """
        turns = []
        segments = stt_data.get("segments", [])
        
        current_customer_text = None
        current_agent_text = None
        turn_index = 0
        
        for segment in segments:
            speaker = segment.get("speaker", "").lower()
            text = segment.get("text", "").strip()
            
            if not text:
                continue
            
            if speaker == "customer":
                # 손님 발화 시작
                # 이전 Turn이 있으면 저장
                if current_customer_text is not None:
                    turns.append(Turn(
                        turn_index=turn_index,
                        customer_text=current_customer_text,
                        agent_text=current_agent_text,
                        timestamp=segment.get("timestamp")
                    ))
                    turn_index += 1
                
                current_customer_text = text
                current_agent_text = None
            
            elif speaker == "agent":
                # 상담원 발화는 현재 Turn에 추가
                if current_agent_text:
                    current_agent_text += " " + text
                else:
                    current_agent_text = text
        
        # 마지막 Turn 저장
        if current_customer_text is not None:
            turns.append(Turn(
                turn_index=turn_index,
                customer_text=current_customer_text,
                agent_text=current_agent_text,
                timestamp=segments[-1].get("timestamp") if segments else None
            ))
        
        return turns
    
    def split_simple_text(self, text: str) -> List[Turn]:
        """
        간단한 텍스트를 Turn으로 분할 (테스트용)
        
        Args:
            text: 텍스트 (형식: "고객: ... 상담사: ...")
        
        Returns:
            Turn 리스트
        """
        turns = []
        import re
        
        # 화자 태그 패턴
        customer_pattern = r'고객[:：]\s*(.+?)(?=상담사[:：]|$)'
        agent_pattern = r'상담사[:：]\s*(.+?)(?=고객[:：]|$)'
        
        customer_matches = list(re.finditer(customer_pattern, text, re.DOTALL))
        agent_matches = list(re.finditer(agent_pattern, text, re.DOTALL))
        
        turn_index = 0
        for customer_match in customer_matches:
            customer_text = customer_match.group(1).strip()
            
            # 해당 손님 발화 다음의 상담원 발화 찾기
            agent_text = None
            customer_end = customer_match.end()
            for agent_match in agent_matches:
                if agent_match.start() > customer_end:
                    agent_text = agent_match.group(1).strip()
                    break
            
            turns.append(Turn(
                turn_index=turn_index,
                customer_text=customer_text,
                agent_text=agent_text
            ))
            turn_index += 1
        
        # 태그가 없으면 전체를 손님 발화로 간주
        if not turns:
            sentences = re.split(r'[.!?。！？]\s*', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            for i, sentence in enumerate(sentences):
                turns.append(Turn(
                    turn_index=i,
                    customer_text=sentence
                ))
        
        return turns


class TextSplitter:
    """
    텍스트 분할기
    
    간단한 텍스트를 문장 단위로 분할하고, 화자별로 구분합니다.
    """
    
    def __init__(self):
        """텍스트 분할기 초기화"""
        pass
    
    def split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            문장 리스트
        """
        import re
        # 문장 구분자로 분할 (마침표, 느낌표, 물음표 등)
        sentences = re.split(r'[.!?。！？]\s+', text)
        # 빈 문장 제거 및 공백 제거
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences if sentences else [text.strip()] if text.strip() else []
    
    def split_by_speaker(self, text: str) -> Tuple[List[str], List[str]]:
        """
        텍스트를 화자별로 분할
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            (customer_sentences, agent_sentences) 튜플
        """
        import re
        
        customer_sentences = []
        agent_sentences = []
        
        # 화자 태그 패턴 (고객/상담사 구분)
        customer_pattern = r'(?:고객|customer|손님)[:：]\s*(.+?)(?=(?:상담사|agent|상담원)[:：]|$)'
        agent_pattern = r'(?:상담사|agent|상담원)[:：]\s*(.+?)(?=(?:고객|customer|손님)[:：]|$)'
        
        customer_matches = re.findall(customer_pattern, text, re.DOTALL | re.IGNORECASE)
        agent_matches = re.findall(agent_pattern, text, re.DOTALL | re.IGNORECASE)
        
        # 고객 발화 처리
        for match in customer_matches:
            text_part = match.strip()
            if text_part:
                # 문장 단위로 추가 분할
                sentences = self.split_sentences(text_part)
                customer_sentences.extend(sentences)
        
        # 상담원 발화 처리
        for match in agent_matches:
            text_part = match.strip()
            if text_part:
                # 문장 단위로 추가 분할
                sentences = self.split_sentences(text_part)
                agent_sentences.extend(sentences)
        
        # 태그가 없으면 전체를 고객 발화로 간주 (문장 단위로 분할)
        if not customer_sentences and not agent_sentences:
            sentences = self.split_sentences(text)
            customer_sentences = sentences
        
        return customer_sentences, agent_sentences
