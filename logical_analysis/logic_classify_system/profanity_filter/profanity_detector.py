"""
욕설 감지 통합 인터페이스

Korcen + Baseline 규칙을 통합하여 욕설을 감지 (HEAD 기반)
Korcen 필터와 Baseline 규칙을 통합한 빠른 욕설 감지 (logic 기능 통합)
"""

from typing import Optional
import logging

from .baseline_rules import ProfanityBaselineRules
from ..data.data_structures import ProfanityResult

logger = logging.getLogger(__name__)


class ProfanityDetector:
    
    def __init__(self, use_korcen: bool = False):
        """
        욕설 감지기 초기화
        
        Args:
            use_korcen: Korcen 사용 여부 (HEAD: 기본 False, logic: 기본 True)
        """
        self.use_korcen = use_korcen
        self.korcen_filter = None
        
        # Korcen 필터 초기화
        if use_korcen:
            try:
                from .korcen_filter import KorcenFilter
                self.korcen_filter = KorcenFilter()
            except ImportError as e:
                self.use_korcen = False
            except Exception as e:
                self.use_korcen = False
        
        print(f"korcen 사용여부: {self.use_korcen}")
        
        self.baseline_rules = ProfanityBaselineRules()
    
    def detect(self, text: str) -> ProfanityResult:
        """
        욕설 감지 (통합) (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            ProfanityResult (is_profanity, category, confidence, method)
        """
        if not text or not text.strip():
            print("분석할 텍스트가 없습니다.")
            return ProfanityResult(
                is_profanity=False,
                category=None,
                confidence=0.0,
                method=None
            )
        
        # 1. Korcen 시도 (구현 시)
        if self.use_korcen and self.korcen_filter:
            try:
                # HEAD: check_profanity 메서드
                if hasattr(self.korcen_filter, 'check_profanity'):
                    result = self.korcen_filter.check_profanity(text)
                    if result[0]:  # 욕설 감지
                        return ProfanityResult(
                            is_profanity=True,
                            category=result[1],
                            confidence=result[2],
                            method="korcen"
                        )
                # logic: detect 메서드
                elif hasattr(self.korcen_filter, 'detect'):
                    result = self.korcen_filter.detect(text)
                    if result:
                        return result
                    
            except Exception as e:
                # Korcen 실패 시 Baseline으로 폴백
                print(f"Korcen 필터 실행 중 오류 발생: {e}. Baseline 규칙으로 전환합니다.")
                logger.warning(f"Korcen 필터 실행 중 오류 발생: {e}. Baseline 규칙으로 전환합니다.")
        
        # 2. Baseline 규칙 사용 (모듈 내부 규칙)
        # HEAD 방식: detect_profanity 사용

        print("Baseline 기반 profanity detector 실행중...")
        is_prof, category, confidence = self.baseline_rules.detect_profanity(text)
        if is_prof:
            return ProfanityResult(
                is_profanity=True,
                category=category,
                confidence=confidence,
                method="baseline"
            )
        else:
            print("prof 감지된 것 없음.")
        
        # logic 방식: detect 메서드도 시도
        result = self.baseline_rules.detect(text)
        print(f"분석 대상: {text}")
        if result:
            print(f"분석 텍스트에서 profanity 감지 됨.")
            return result
        else:
            print(f"분석된 prof 없음\n")

        return ProfanityResult(
            is_profanity=False,
            category=None,
            confidence=0.0,
            method=None
        )
    
    def get_hint(self, sentence: str) -> Optional[str]:
        """
        감지 힌트 반환 (Korcen 힌트) (logic: 추가)
        
        Args:
            sentence: 분석할 문장
        
        Returns:
            힌트 문자열 (PROFANITY_DETECTED, SEXUAL_DETECTED, HATE_DETECTED, VIOLENCE_THREAT) 또는 None
        """
        result = self.detect(sentence)
        if result and result.method == "korcen":
            return result.category
        return None
