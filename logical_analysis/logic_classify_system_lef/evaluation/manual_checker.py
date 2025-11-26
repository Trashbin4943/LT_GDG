"""
매뉴얼 준수 여부 확인

상담사가 시스템 매뉴얼에 따라 적절히 대응했는지 확인
"""

from typing import Dict, Optional
import json
from pathlib import Path


class ManualChecker:
    """매뉴얼 체커"""
    
    # 매뉴얼 정의 (임시, 향후 JSON 파일로 이동)
    MANUAL: Dict[str, Dict] = {
        "INQUIRY": {
            "required_phrases": ["안내드리겠습니다", "확인해보겠습니다"],
            "required_keywords": ["가격", "정책", "절차", "정보"],
            "procedure": ["고객 질문 확인", "정보 제공", "추가 문의 확인"]
        },
        "COMPLAINT": {
            "required_phrases": ["불편을 드려 죄송합니다", "해결 방안을 제시하겠습니다"],
            "required_keywords": ["불편", "사과", "해결"],
            "procedure": ["불만 내용 확인", "공감 표현", "해결 방안 제시", "사과"]
        },
        "REQUEST": {
            "required_phrases": ["처리해드리겠습니다", "절차를 안내드리겠습니다"],
            "required_keywords": ["처리", "절차", "안내"],
            "procedure": ["요청 확인", "절차 안내", "처리"]
        },
        "CLARIFICATION": {
            "required_phrases": ["다시 설명드리겠습니다", "이해하셨는지 확인하겠습니다"],
            "required_keywords": ["설명", "확인", "이해"],
            "procedure": ["추가 설명", "이해도 확인"]
        },
        "CONFIRMATION": {
            "required_phrases": ["확인해드리겠습니다", "맞습니다"],
            "required_keywords": ["확인", "맞습니다"],
            "procedure": ["확인 내용 제시", "정확성 확인"]
        },
        "CLOSING": {
            "required_phrases": ["감사합니다", "추가 문의 있으시면 연락주세요"],
            "required_keywords": ["감사", "문의"],
            "procedure": ["종료 확인", "추가 문의 확인", "인사"]
        }
    }
    
    def __init__(self, manual_path: Optional[str] = None):
        """
        매뉴얼 체커 초기화
        
        Args:
            manual_path: 매뉴얼 JSON 파일 경로 (향후 구현)
        """
        if manual_path and Path(manual_path).exists():
            # JSON 파일에서 로드 (향후 구현)
            # with open(manual_path, 'r', encoding='utf-8') as f:
            #     self.manual = json.load(f)
            self.manual = self.MANUAL
        else:
            self.manual = self.MANUAL
    
    def check_compliance(self, label: str, agent_text: str) -> float:
        """
        매뉴얼 준수 여부 확인
        
        Args:
            label: Normal Label
            agent_text: 상담사 발화
        
        Returns:
            점수 (0.0-1.0)
        """
        if label not in self.manual:
            return 0.5  # 기본값
        
        manual_data = self.manual[label]
        agent_lower = agent_text.lower()
        
        # 필수 표현 사용 여부 확인
        required_phrases = manual_data.get("required_phrases", [])
        phrase_score = self._check_phrases(agent_lower, required_phrases)
        
        # 필수 키워드 사용 여부 확인
        required_keywords = manual_data.get("required_keywords", [])
        keyword_score = self._check_keywords(agent_lower, required_keywords)
        
        # 절차 순서 확인 (간단한 구현)
        procedure_score = self._check_procedure(label, agent_lower)
        
        # 종합 점수 (가중치: phrase 40%, keyword 30%, procedure 30%)
        total_score = phrase_score * 0.4 + keyword_score * 0.3 + procedure_score * 0.3
        
        return total_score
    
    def _check_phrases(self, agent_text: str, required_phrases: list) -> float:
        """
        필수 표현 사용 여부 확인
        
        Returns:
            점수 (0.0-1.0)
        """
        if not required_phrases:
            return 0.7  # 기본값
        
        found_count = sum(1 for phrase in required_phrases if phrase in agent_text)
        
        if found_count == 0:
            return 0.2
        elif found_count == len(required_phrases):
            return 1.0
        else:
            return 0.5 + (found_count / len(required_phrases)) * 0.3
    
    def _check_keywords(self, agent_text: str, required_keywords: list) -> float:
        """
        필수 키워드 사용 여부 확인
        
        Returns:
            점수 (0.0-1.0)
        """
        if not required_keywords:
            return 0.7  # 기본값
        
        found_count = sum(1 for keyword in required_keywords if keyword in agent_text)
        
        if found_count == 0:
            return 0.3
        elif found_count >= len(required_keywords) * 0.5:
            return 1.0
        else:
            return 0.5 + (found_count / len(required_keywords)) * 0.4
    
    def _check_procedure(self, label: str, agent_text: str) -> float:
        """
        절차 순서 확인 (간단한 구현)
        
        Returns:
            점수 (0.0-1.0)
        """
        # 향후 더 정교한 절차 순서 확인 구현 필요
        # 현재는 키워드 기반으로 간단히 확인
        
        if label not in self.manual:
            return 0.5
        
        procedure = self.manual[label].get("procedure", [])
        if not procedure:
            return 0.7
        
        # 절차 키워드가 포함되어 있는지 확인
        procedure_keywords = []
        for step in procedure:
            procedure_keywords.extend(step.split())
        
        found_count = sum(1 for kw in procedure_keywords if kw in agent_text)
        
        if found_count == 0:
            return 0.3
        elif found_count >= len(procedure_keywords) * 0.5:
            return 1.0
        else:
            return 0.5 + (found_count / len(procedure_keywords)) * 0.4


