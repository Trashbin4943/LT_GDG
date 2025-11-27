"""
발화 의도 분류용 Baseline 규칙

특수 Label 감지를 위한 규칙만 포함 (HEAD 기반)
UNREASONABLE_DEMAND, REPETITION 감지 (logic 기능 통합)
"""

from typing import List, Tuple, Optional
import logging

from ..data.data_structures import ClassificationResult
from ..config.labels import SpecialLabel, LabelType

logger = logging.getLogger(__name__)


class IntentBaselineRules:
    """발화 의도 분류용 Baseline 규칙 (HEAD 기반 + logic 기능 통합)"""
    
    # 반복성 감지 키워드 (HEAD: 유지)
    REPETITION_INDICATORS = [
        "앞선 통화에서도 말씀드렸다시피", "이전에도 말씀드렸는데",
        "또 같은 말씀", "계속 같은 얘기", "반복해서 말씀드리는데",
        "또 물어보는 거예요", "아까도 말했는데"
    ]
    
    # 무리한 요구 감지 키워드 (HEAD: 유지)
    # 강한 표현 (1개만 있어도 감지, HIGH 심각도)
    UNREASONABLE_DEMAND_STRONG = [
        "지금 당장", "바로", "즉시", "당장", "지금",
        "FBI", "경찰", "법원", "검찰", "고소", "고발",
        "불가능한데", "권한 밖", "할 수 없는데", "안 된다고",
        "특별히", "예외로", "빠르게 해줘", "급하게"
    ]
    
    # 일반적인 무리한 요구 표현 (2개 이상 감지, MEDIUM 심각도) (HEAD: 유지)
    UNREASONABLE_DEMAND_INDICATORS = [
        "공짜로", "무료로", "할인", "보상", "배상",
        "책임져", "해결해줘", "처리해줘", "해결 못하면"
    ]
    
    # logic: 추가 키워드
    UNREASONABLE_DEMAND_KEYWORDS = [
        "지금 당장", "바로", "즉시", "지금", "당장", "금방",
        "지금 해줘", "바로 해줘", "당장 해줘"
    ]
    
    # logic: 강요 표현
    PRESSURE_KEYWORDS = [
        "해야 해", "해야 한다", "안 되면", "안 하면", "시발",
        "화나게 하지 마", "빨리", "급하다"
    ]
    
    # 부당성/무관성 감지 키워드 (HEAD: 유지)
    IRRELEVANCE_INDICATORS = [
        "독도에 보내달라", "돈이 없는데", "상관없는 얘기",
        "이건 왜 물어보는 거예요", "맥락 없음"
    ]
    
    @staticmethod
    def detect_special_labels(
        text: str,
        session_context: Optional[List[str]] = None,
        return_type: str = "list"  # "list" (HEAD) or "classification" (logic)
    ):
        """
        특수 Label 감지 (Baseline 규칙 기반) (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            text: 분석할 텍스트
            session_context: 세션 맥락 (반복성 감지용)
            return_type: 반환 타입 ("list" 또는 "classification")
        
        Returns:
            HEAD 방식: [(label, confidence), ...] 리스트
            logic 방식: ClassificationResult 또는 None
        """
        if not text:
            return [] if return_type == "list" else None
        
        results = []
        text_lower = text.lower()
        
        # 1. 반복성 감지 (HEAD 로직 유지)
        repetition_count = sum(1 for indicator in IntentBaselineRules.REPETITION_INDICATORS 
                               if indicator in text_lower)
        
        if session_context:
            # 이전 대화와의 유사도 체크 (간단한 키워드 기반)
            similar_topics = sum(1 for prev_text in session_context[-3:] 
                                 if any(word in prev_text and word in text 
                                       for word in text.split() if len(word) > 3))
            
            if repetition_count > 0 or similar_topics >= 2:
                confidence = min(0.5 + (repetition_count + similar_topics) * 0.15, 1.0)
                results.append(("REPETITION", confidence))
        else:
            # 세션 맥락이 없어도 반복 표현만으로 감지
            if repetition_count > 0:
                confidence = min(0.4 + repetition_count * 0.2, 1.0)
                results.append(("REPETITION", confidence))
        
        # 2. 무리한 요구 감지 (HEAD 로직 유지)
        strong_unreasonable = [kw for kw in IntentBaselineRules.UNREASONABLE_DEMAND_STRONG 
                              if kw in text_lower]
        if strong_unreasonable:
            # 강한 표현이 있으면 HIGH 심각도
            confidence = min(0.7 + len(strong_unreasonable) * 0.1, 1.0)
            results.append(("UNREASONABLE_DEMAND", confidence))
        else:
            # 일반적인 무리한 요구 표현 (2개 이상 감지)
            unreasonable_count = sum(1 for kw in IntentBaselineRules.UNREASONABLE_DEMAND_INDICATORS 
                                    if kw in text_lower)
            if unreasonable_count >= 2:
                confidence = min(0.4 + unreasonable_count * 0.2, 1.0)
                results.append(("UNREASONABLE_DEMAND", confidence))
            elif unreasonable_count == 1:
                # 1개만 있어도 LOW 심각도로 감지
                confidence = 0.3
                results.append(("UNREASONABLE_DEMAND", confidence))
        
        # logic: 추가 무리한 요구 감지 로직
        unreasonable_detected = False
        for keyword in IntentBaselineRules.UNREASONABLE_DEMAND_KEYWORDS:
            if keyword in text_lower:
                unreasonable_detected = True
                break
        
        if unreasonable_detected:
            # 강요 표현 확인
            has_pressure = any(keyword in text_lower for keyword in IntentBaselineRules.PRESSURE_KEYWORDS)
            confidence = 0.90 if has_pressure else 0.75
            
            # 중복 제거 (이미 추가된 경우 더 높은 신뢰도 사용)
            existing = [r for r in results if r[0] == "UNREASONABLE_DEMAND"]
            if existing:
                if confidence > existing[0][1]:
                    results = [r for r in results if r[0] != "UNREASONABLE_DEMAND"]
                    results.append(("UNREASONABLE_DEMAND", confidence))
            else:
                results.append(("UNREASONABLE_DEMAND", confidence))
        
        # 3. 부당성/무관성 감지 (HEAD: 유지)
        irrelevance_count = sum(1 for kw in IntentBaselineRules.IRRELEVANCE_INDICATORS 
                               if kw in text_lower)
        if irrelevance_count > 0:
            confidence = min(0.3 + irrelevance_count * 0.25, 1.0)
            results.append(("IRRELEVANCE", confidence))
        
        # logic: 반복 감지 (세션 맥락 기반)
        if session_context and len(session_context) >= 2:
            recent_context = session_context[-3:]
            text_normalized = text.strip().lower()
            
            for ctx_text in recent_context:
                ctx_normalized = ctx_text.strip().lower()
                # 유사도 간단 계산 (같은 문장이면 반복)
                if text_normalized == ctx_normalized:
                    # 중복 제거
                    existing = [r for r in results if r[0] == "REPETITION"]
                    if existing:
                        if 0.85 > existing[0][1]:
                            results = [r for r in results if r[0] != "REPETITION"]
                            results.append(("REPETITION", 0.85))
                    else:
                        results.append(("REPETITION", 0.85))
                    break
                
                # 부분 일치 확인 (70% 이상 유사)
                similarity = IntentBaselineRules._calculate_similarity(text_normalized, ctx_normalized)
                if similarity > 0.7:
                    existing = [r for r in results if r[0] == "REPETITION"]
                    if existing:
                        if 0.75 > existing[0][1]:
                            results = [r for r in results if r[0] != "REPETITION"]
                            results.append(("REPETITION", 0.75))
                    else:
                        results.append(("REPETITION", 0.75))
                    break
        
        # 반환 타입에 따라 변환
        if return_type == "classification":
            if not results:
                return None
            
            # 가장 높은 신뢰도의 Label 선택
            label, confidence = max(results, key=lambda x: x[1])
            
            return ClassificationResult(
                label=label,
                label_type=LabelType.SPECIAL.value,
                confidence=confidence,
                text=text
            )
        else:
            # HEAD 방식: List[Tuple] 반환
            return results
    
    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """간단한 유사도 계산 (Levenshtein 기반) (logic: 추가)"""
        if not text1 or not text2:
            return 0.0
        
        # 간단한 Jaccard 유사도
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
