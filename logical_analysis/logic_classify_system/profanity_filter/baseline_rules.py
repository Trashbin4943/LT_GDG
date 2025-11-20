"""
Profanity Baseline 규칙

키워드 기반 욕설 감지 규칙
"""
from typing import Optional
from logic_classify_system.data.data_structures import ProfanityResult
from logic_classify_system.config.labels import SpecialLabel
import logging

logger = logging.getLogger(__name__)


class ProfanityBaselineRules:
    """Profanity Baseline 규칙"""
    
    # 욕설 키워드 (예시)
    PROFANITY_KEYWORDS = [
        "시발", "개새끼", "병신", "멍청이", "바보", "천치",
        "좆", "개", "놈", "새끼", "년", "년놈"
    ]
    
    # 성적 표현 키워드
    SEXUAL_KEYWORDS = [
        "보지", "자지", "섹스", "성교", "포르노"
    ]
    
    # 폭력 위협 키워드
    VIOLENCE_KEYWORDS = [
        "죽여", "때려", "폭행", "협박", "위협"
    ]
    
    # 혐오 표현 키워드
    HATE_KEYWORDS = [
        "짱깨", "쪽바리", "흑형", "흑인", "장애인"
    ]
    
    @classmethod
    def detect(cls, text: str) -> Optional[ProfanityResult]:
        """
        Baseline 규칙으로 욕설 감지
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            ProfanityResult 또는 None (감지 실패 시)
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # 성적 표현 확인
        for keyword in cls.SEXUAL_KEYWORDS:
            if keyword in text_lower:
                return ProfanityResult(
                    is_profanity=True,
                    category=SpecialLabel.SEXUAL_HARASSMENT.value,
                    confidence=0.85,
                    method="baseline",
                    text=text
                )
        
        # 폭력 위협 확인
        for keyword in cls.VIOLENCE_KEYWORDS:
            if keyword in text_lower:
                return ProfanityResult(
                    is_profanity=True,
                    category=SpecialLabel.VIOLENCE_THREAT.value,
                    confidence=0.85,
                    method="baseline",
                    text=text
                )
        
        # 혐오 표현 확인
        for keyword in cls.HATE_KEYWORDS:
            if keyword in text_lower:
                return ProfanityResult(
                    is_profanity=True,
                    category=SpecialLabel.HATE_SPEECH.value,
                    confidence=0.85,
                    method="baseline",
                    text=text
                )
        
        # 일반 욕설 확인
        for keyword in cls.PROFANITY_KEYWORDS:
            if keyword in text_lower:
                return ProfanityResult(
                    is_profanity=True,
                    category=SpecialLabel.PROFANITY.value,
                    confidence=0.80,
                    method="baseline",
                    text=text
                )
        
        return None
