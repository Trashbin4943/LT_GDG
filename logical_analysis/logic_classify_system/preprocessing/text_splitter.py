"""
텍스트 분할 및 화자 구분

STT 결과 텍스트를 문장 단위로 분할하고 화자를 구분
"""
from typing import List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class TextSplitter:
    """텍스트 분할 및 화자 구분"""
    
    def __init__(self):
        """초기화"""
        # 화자 태그 패턴
        self.speaker_pattern = re.compile(r'^(고객|상담사|Customer|Agent)[:：]\s*(.+)$', re.MULTILINE)
    
    def split_text(self, text: str) -> Tuple[List[str], List[str]]:
        """
        텍스트를 분할하고 화자 구분
        
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
        
        # 줄바꿈 기준으로 분할
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
                # (또는 이전 화자 추론 등으로 처리 가능)
                customer_sentences.append(line)
        
        return customer_sentences, agent_sentences
    
    def extract_customer_sentences(self, text: str) -> List[str]:
        """
        고객 발화만 추출
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            고객 발화 리스트
        """
        customer_sentences, _ = self.split_text(text)
        return customer_sentences
    
    def extract_agent_sentences(self, text: str) -> List[str]:
        """
        상담사 발화만 추출
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            상담사 발화 리스트
        """
        _, agent_sentences = self.split_text(text)
        return agent_sentences
