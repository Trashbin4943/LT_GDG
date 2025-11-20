"""
Korcen 필터

단어 단위 패턴 매칭을 통한 빠른 욕설 감지
"""
from typing import Optional, Tuple
from logic_classify_system.data.data_structures import ProfanityResult
import logging

logger = logging.getLogger(__name__)


class KorcenFilter:
    """Korcen 필터 (4개 레벨: general, sexual, race, special)"""
    
    # Korcen 힌트 매핑
    HINT_MAPPING = {
        "general": "PROFANITY_DETECTED",
        "sexual": "SEXUAL_DETECTED",
        "race": "HATE_DETECTED",
        "special": "VIOLENCE_THREAT"
    }
    
    def __init__(self, use_korcen: bool = True):
        """
        초기화
        
        Args:
            use_korcen: Korcen 사용 여부
        """
        self.use_korcen = use_korcen
        self.korcen = None
        
        if use_korcen:
            try:
                import korcen
                self.korcen = korcen
                logger.info("Korcen 필터 로드 완료")
            except ImportError:
                logger.warning("Korcen 라이브러리를 찾을 수 없습니다. pip install korcen을 실행하세요.")
                self.use_korcen = False
                self.korcen = None
    
    def detect(self, text: str) -> Optional[ProfanityResult]:
        """
        Korcen으로 욕설 감지
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            ProfanityResult 또는 None (감지 실패 시)
        """
        if not self.use_korcen or self.korcen is None:
            return None
        
        if not text:
            return None
        
        try:
            # Korcen 감지 (예시 - 실제 API는 다를 수 있음)
            # korcen.check() 또는 korcen.detect() 사용
            result = self.korcen.check(text)
            
            if result and result.get("is_profanity", False):
                level = result.get("level", "general")
                confidence = result.get("confidence", 0.80)
                category = self.HINT_MAPPING.get(level, "PROFANITY_DETECTED")
                
                return ProfanityResult(
                    is_profanity=True,
                    category=category,
                    confidence=confidence,
                    method="korcen",
                    text=text
                )
        except Exception as e:
            logger.error(f"Korcen 감지 실패: {e}")
            return None
        
        return None
    
    def check_with_levels(self, text: str) -> Optional[Tuple[str, float]]:
        """
        레벨별 감지 (4개 레벨)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            (level, confidence) 또는 None
        """
        if not self.use_korcen or self.korcen is None:
            return None
        
        if not text:
            return None
        
        try:
            result = self.korcen.check(text)
            
            if result and result.get("is_profanity", False):
                level = result.get("level", "general")
                confidence = result.get("confidence", 0.80)
                return (level, confidence)
        except Exception as e:
            logger.error(f"Korcen 레벨 감지 실패: {e}")
            return None
        
        return None
