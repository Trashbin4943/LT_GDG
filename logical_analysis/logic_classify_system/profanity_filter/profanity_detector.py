"""
욕설 감지 통합 인터페이스

기존 profanity_detector.py에서 복사 (Turn 단위 분석용)
"""

from typing import Optional
from .baseline_rules import ProfanityBaselineRules
from ..data.data_structures import ProfanityResult


class ProfanityDetector:
    """욕설 감지기"""
    
    def __init__(self, use_korcen: bool = False):
        """
        욕설 감지기 초기화
        
        Args:
            use_korcen: Korcen 사용 여부 (기본: False, Korcen 미구현 상태)
        """
        self.use_korcen = use_korcen
        self.korcen_filter = None
        
        # Korcen 필터 초기화
        if use_korcen:
            try:
                from .korcen_filter import KorcenFilter
                self.korcen_filter = KorcenFilter()
            except ImportError as e:
                print(f"Warning: Korcen 필터를 로드할 수 없습니다. Baseline 규칙만 사용합니다. ({e})")
                self.use_korcen = False
            except Exception as e:
                print(f"Warning: Korcen 필터 초기화 중 오류 발생: {e}. Baseline 규칙만 사용합니다.")
                self.use_korcen = False
        
        # Baseline 규칙은 모듈 내부에 포함 (의존성 없음)
        self.baseline_rules = ProfanityBaselineRules()
    
    def detect(self, text: str) -> ProfanityResult:
        """
        욕설 감지 (통합)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            ProfanityResult (is_profanity, category, confidence, method)
        """
        # 1. Korcen 시도 (구현 시)
        if self.use_korcen and self.korcen_filter:
            try:
                result = self.korcen_filter.check_profanity(text)
                if result[0]:  # 욕설 감지
                    return ProfanityResult(
                        is_profanity=True,
                        category=result[1],
                        confidence=result[2],
                        method="korcen"
                    )
            except Exception as e:
                # Korcen 실패 시 Baseline으로 폴백
                print(f"Warning: Korcen 필터 실행 중 오류 발생: {e}. Baseline 규칙으로 전환합니다.")
        
        # 2. Baseline 규칙 사용 (모듈 내부 규칙)
        is_prof, category, confidence = self.baseline_rules.detect_profanity(text)
        if is_prof:
            return ProfanityResult(
                is_profanity=True,
                category=category,
                confidence=confidence,
                method="baseline"
            )
        
        return ProfanityResult(
            is_profanity=False,
            category=None,
            confidence=0.0,
            method=None
        )



