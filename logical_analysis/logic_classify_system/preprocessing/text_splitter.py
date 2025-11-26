"""
문장 단위 분할

STT 결과 텍스트를 문장 단위로 분할하고 화자별로 구분 (HEAD 기반)
텍스트 분할 및 화자 구분 (logic 기능 통합)
"""

from typing import List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class TextSplitter:
    """텍스트 분할기 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(self):
        """텍스트 분할기 초기화"""
        # HEAD: 한국어 문장 종결 기호
        self.sentence_endings = r'[.!?。！？]\s*'
        
        # logic: 화자 태그 패턴
        self.speaker_pattern = re.compile(r'^(고객|상담사|Customer|Agent)[:：]\s*(.+)$', re.MULTILINE)
    
    def split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할 (HEAD: 유지)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            문장 리스트
        """
        # 문장 종결 기호로 분할
        sentences = re.split(self.sentence_endings, text)
        
        # 빈 문장 제거 및 정제
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def split_by_speaker(self, text: str) -> Tuple[List[str], List[str]]:
        """
        화자별로 문장 분할 (고객/상담사 구분) (HEAD: 유지)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            (customer_sentences, agent_sentences)
        """
        customer_sentences = []
        agent_sentences = []
        
        # HEAD: 화자 태그 패턴
        customer_pattern = r'고객[:：]\s*(.+?)(?=상담사[:：]|$)'
        agent_pattern = r'상담사[:：]\s*(.+?)(?=고객[:：]|$)'
        
        customer_matches = re.findall(customer_pattern, text, re.DOTALL)
        agent_matches = re.findall(agent_pattern, text, re.DOTALL)
        
        # 각 매치를 문장으로 분할
        for match in customer_matches:
            customer_sentences.extend(self.split_sentences(match))
        
        for match in agent_matches:
            agent_sentences.extend(self.split_sentences(match))
        
        # 태그가 없으면 전체를 고객 발화로 간주
        if not customer_sentences and not agent_sentences:
            customer_sentences = self.split_sentences(text)
        
        return customer_sentences, agent_sentences
    
    def split_text(self, text: str) -> Tuple[List[str], List[str]]:
        """
        텍스트를 분할하고 화자 구분 (logic: 추가 메서드)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            (customer_sentences, agent_sentences)
            - customer_sentences: 고객 발화 리스트
            - agent_sentences: 상담사 발화 리스트
        """
        if not text or not text.strip():
            return [], []
        
        customer_sentences = []
        agent_sentences = []
        
        # logic: 줄바꿈 기준으로 분할
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 화자 태그 확인
            match = self.speaker_pattern.match(line)
            if match:
                speaker = match.group(1)
                content = match.group(2).strip()
                
                if not content:
                    continue
                
                if speaker in ['고객', 'Customer']:
                    customer_sentences.append(content)
                elif speaker in ['상담사', 'Agent']:
                    agent_sentences.append(content)
            else:
                # 태그가 없는 경우, 기본적으로 고객 발화로 처리
                customer_sentences.append(line)
        
        return customer_sentences, agent_sentences
    
    def extract_customer_sentences(self, text: str) -> List[str]:
        """
        고객 발화만 추출 (logic: 추가)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            고객 발화 리스트
        """
        customer_sentences, _ = self.split_text(text)
        return customer_sentences
    
    def extract_agent_sentences(self, text: str) -> List[str]:
        """
        상담사 발화만 추출 (logic: 추가)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            상담사 발화 리스트
        """
        _, agent_sentences = self.split_text(text)
        return agent_sentences
