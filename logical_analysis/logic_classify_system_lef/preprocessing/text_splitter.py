"""
문장 단위 분할

STT 결과 텍스트를 문장 단위로 분할하고 화자별로 구분
"""

from typing import List, Tuple
import re


class TextSplitter:
    """텍스트 분할기"""
    
    def __init__(self):
        """텍스트 분할기 초기화"""
        # 한국어 문장 종결 기호
        self.sentence_endings = r'[.!?。！？]\s*'
    
    def split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할
        
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
        화자별로 문장 분할 (고객/상담사 구분)
        
        Args:
            text: STT 결과 텍스트
        
        Returns:
            (customer_sentences, agent_sentences)
        """
        # 간단한 구현: "고객:", "상담사:" 같은 태그로 구분
        # 실제 구현 시 STT 결과에 화자 정보가 포함되어야 함
        
        customer_sentences = []
        agent_sentences = []
        
        # 화자 태그 패턴
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


