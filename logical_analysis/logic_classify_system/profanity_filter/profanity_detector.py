"""
욕설 감지 통합 인터페이스

Korcen 필터와 Baseline 규칙을 통합한 빠른 욕설 감지
"""
from typing import Optional
from logic_classify_system.data.data_structures import ProfanityResult
from logic_classify_system.profanity_filter.korcen_filter import KorcenFilter
from logic_classify_system.profanity_filter.baseline_rules import ProfanityBaselineRules
import logging

logger = logging.getLogger(__name__)


class ProfanityDetector:
    """욕설 감지 통합 인터페이스"""
    
    def __init__(self, use_korcen: bool = True):
        """
        초기화
        
        Args:
            use_korcen: Korcen 사용 여부
        """
        self.use_korcen = use_korcen
        self.korcen_filter = KorcenFilter(use_korcen=use_korcen)
        self.baseline_rules = ProfanityBaselineRules()
    
    def detect(self, sentence: str) -> Optional[ProfanityResult]:
        """
        욕설 감지 (Korcen 우선, 실패 시 Baseline 규칙)
        
        Args:
            sentence: 분석할 문장
        
        Returns:
            ProfanityResult 또는 None (감지 실패 시)
        """
        if not sentence or not sentence.strip():
            return None
        
        # 1. Korcen 필터 시도
        if self.use_korcen:
            result = self.korcen_filter.detect(sentence)
            if result:
                return result
        
        # 2. Baseline 규칙 폴백
        result = self.baseline_rules.detect(sentence)
        if result:
            return result
        
        return None
    
    def get_hint(self, sentence: str) -> Optional[str]:
        """
        감지 힌트 반환 (Korcen 힌트)
        
        Args:
            sentence: 분석할 문장
        
        Returns:
            힌트 문자열 (PROFANITY_DETECTED, SEXUAL_DETECTED, HATE_DETECTED, VIOLENCE_THREAT) 또는 None
        """
        result = self.detect(sentence)
        if result and result.method == "korcen":
            return result.category
        return None
