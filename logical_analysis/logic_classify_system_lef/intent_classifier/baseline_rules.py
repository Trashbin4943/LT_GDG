"""
발화 의도 분류용 Baseline 규칙

특수 Label 감지를 위한 규칙만 포함
classification_criteria.py의 일부 규칙만 추출하여 모듈 내부에 포함
"""

from typing import List, Tuple, Optional


class IntentBaselineRules:
    """발화 의도 분류용 Baseline 규칙"""
    
    # 반복성 감지 키워드
    REPETITION_INDICATORS = [
        "앞선 통화에서도 말씀드렸다시피", "이전에도 말씀드렸는데",
        "또 같은 말씀", "계속 같은 얘기", "반복해서 말씀드리는데",
        "또 물어보는 거예요", "아까도 말했는데"
    ]
    
    # 무리한 요구 감지 키워드
    # 강한 표현 (1개만 있어도 감지, HIGH 심각도)
    UNREASONABLE_DEMAND_STRONG = [
        "지금 당장", "바로", "즉시", "당장", "지금",
        "FBI", "경찰", "법원", "검찰", "고소", "고발",
        "불가능한데", "권한 밖", "할 수 없는데", "안 된다고",
        "특별히", "예외로", "빠르게 해줘", "급하게"
    ]
    
    # 일반적인 무리한 요구 표현 (2개 이상 감지, MEDIUM 심각도)
    UNREASONABLE_DEMAND_INDICATORS = [
        "공짜로", "무료로", "할인", "보상", "배상",
        "책임져", "해결해줘", "처리해줘", "해결 못하면"
    ]
    
    # 부당성/무관성 감지 키워드
    IRRELEVANCE_INDICATORS = [
        "독도에 보내달라", "돈이 없는데", "상관없는 얘기",
        "이건 왜 물어보는 거예요", "맥락 없음"
    ]
    
    @staticmethod
    def detect_special_labels(text: str, session_context: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        특수 Label 감지 (Baseline 규칙 기반)
        
        Args:
            text: 분석할 텍스트
            session_context: 세션 맥락 (반복성 감지용)
        
        Returns:
            [(label, confidence), ...] 리스트
            - label: 특수 Label (REPETITION, UNREASONABLE_DEMAND, IRRELEVANCE)
            - confidence: 신뢰도 (0.0-1.0)
        """
        results = []
        text_lower = text.lower()
        
        # 1. 반복성 감지
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
        
        # 2. 무리한 요구 감지
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
        
        # 3. 부당성/무관성 감지
        irrelevance_count = sum(1 for kw in IntentBaselineRules.IRRELEVANCE_INDICATORS 
                               if kw in text_lower)
        if irrelevance_count > 0:
            confidence = min(0.3 + irrelevance_count * 0.25, 1.0)
            results.append(("IRRELEVANCE", confidence))
        
        return results


