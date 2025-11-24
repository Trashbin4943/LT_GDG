"""
발화 의도 분류용 Baseline 규칙

Turn 단위 분석을 위해 반복성 감지를 키워드만으로 제한
"""

from typing import List, Tuple, Optional


class IntentBaselineRules:
    """발화 의도 분류용 Baseline 규칙"""
    
    # 반복성 감지 키워드 (Turn 단위: 키워드만 감지)
    REPETITION_INDICATORS = [
        "앞선 통화에서도 말씀드렸다시피", "이전에도 말씀드렸는데",
        "또 같은 말씀", "계속 같은 얘기", "반복해서 말씀드리는데",
        "또 물어보는 거예요", "아까도 말했는데"
    ]
    
    # 무리한 요구 감지 키워드 (실제로 무리한 요구만)
    # 법적/위협적 표현 (1개만 있어도 감지, HIGH 심각도)
    UNREASONABLE_DEMAND_STRONG = [
        "FBI", "경찰", "법원", "검찰", "고소", "고발",
        "불가능한데", "권한 밖", "할 수 없는데", "안 된다고",
        "특별히", "예외로"
    ]
    
    # 일반적인 무리한 요구 표현 (2개 이상 감지, MEDIUM 심각도)
    UNREASONABLE_DEMAND_INDICATORS = [
        "공짜로", "무료로", "할인", "보상", "배상",
        "책임져", "해결 못하면"
    ]
    
    # 부당성/무관성 감지 키워드
    IRRELEVANCE_INDICATORS = [
        "독도에 보내달라", "돈이 없는데", "상관없는 얘기",
        "이건 왜 물어보는 거예요", "맥락 없음"
    ]
    
    # Normal Label: REQUEST (요청) 감지 키워드
    REQUEST_KEYWORDS = [
        "지금 당장", "바로", "즉시", "당장", "지금", "빠르게 해줘", "급하게",
        "해결해줘", "처리해줘", "부탁드려요", "요청드려요",
        "도와주세요", "해주세요", "부탁합니다"
    ]
    
    # Normal Label: COMPLAINT (불만) 감지 키워드
    COMPLAINT_KEYWORDS = [
        "불만", "불편", "문제", "이상하네요", "이상한데",
        "안 되는데", "안 되네요", "제대로 안 되는데",
        "왜 이래요", "왜 이러세요", "불만이 있어요",
        "항의", "민원", "불만사항"
    ]
    
    # Normal Label: CLARIFICATION (명확화 요청) 감지 키워드
    CLARIFICATION_KEYWORDS = [
        "무슨 뜻이에요", "무슨 말씀이에요", "뭔 말이에요",
        "설명해주세요", "이해가 안 돼요", "뭐라는 거예요",
        "다시 말씀해주세요", "다시 설명해주세요",
        "잘 모르겠어요", "잘 모르겠는데"
    ]
    
    # Normal Label: CONFIRMATION (확인) 감지 키워드
    CONFIRMATION_KEYWORDS = [
        "맞나요", "맞죠", "맞나", "맞는지",
        "확인해주세요", "확인 부탁드려요",
        "이거 맞나요", "제대로 된 건가요",
        "맞는 건가요", "맞는지 확인"
    ]
    
    # Normal Label: CLOSING (종료) 감지 키워드
    CLOSING_KEYWORDS = [
        "감사합니다", "고맙습니다", "수고하셨습니다",
        "끝내주세요", "끝내고 싶어요", "종료하고 싶어요",
        "그럼 이만", "그럼 이 정도로", "끝내면 될까요",
        "다음에 다시", "나중에 다시"
    ]
    
    # Normal Label: INQUIRY (문의) 감지 키워드 (기본값)
    INQUIRY_KEYWORDS = [
        "어떻게", "언제", "어디서", "뭐예요", "뭔가요",
        "물어보고 싶어요", "궁금한데", "알고 싶어요",
        "문의", "질문", "궁금해요"
    ]
    
    @staticmethod
    def detect_normal_labels(text: str, session_context: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        Normal Label 감지 (Baseline 규칙 기반)
        
        Args:
            text: 분석할 텍스트 (해당 Turn만)
            session_context: 세션 맥락 (선택사항, 최소 사용)
        
        Returns:
            [(label, confidence), ...] 리스트
            - label: Normal Label (INQUIRY, REQUEST, COMPLAINT, CLARIFICATION, CONFIRMATION, CLOSING)
            - confidence: 신뢰도 (0.0-1.0)
        """
        results = []
        text_lower = text.lower()
        
        # 1. REQUEST (요청) 감지
        request_keywords = [kw for kw in IntentBaselineRules.REQUEST_KEYWORDS if kw in text_lower]
        if request_keywords:
            confidence = min(0.6 + len(request_keywords) * 0.15, 0.9)
            results.append(("REQUEST", confidence))
        
        # 2. COMPLAINT (불만) 감지
        complaint_keywords = [kw for kw in IntentBaselineRules.COMPLAINT_KEYWORDS if kw in text_lower]
        if complaint_keywords:
            confidence = min(0.6 + len(complaint_keywords) * 0.15, 0.9)
            results.append(("COMPLAINT", confidence))
        
        # 3. CLARIFICATION (명확화 요청) 감지
        clarification_keywords = [kw for kw in IntentBaselineRules.CLARIFICATION_KEYWORDS if kw in text_lower]
        if clarification_keywords:
            confidence = min(0.6 + len(clarification_keywords) * 0.15, 0.9)
            results.append(("CLARIFICATION", confidence))
        
        # 4. CONFIRMATION (확인) 감지
        confirmation_keywords = [kw for kw in IntentBaselineRules.CONFIRMATION_KEYWORDS if kw in text_lower]
        if confirmation_keywords:
            confidence = min(0.6 + len(confirmation_keywords) * 0.15, 0.9)
            results.append(("CONFIRMATION", confidence))
        
        # 5. CLOSING (종료) 감지
        closing_keywords = [kw for kw in IntentBaselineRules.CLOSING_KEYWORDS if kw in text_lower]
        if closing_keywords:
            confidence = min(0.7 + len(closing_keywords) * 0.1, 0.9)
            results.append(("CLOSING", confidence))
        
        # 6. INQUIRY (문의) 감지 (기본값)
        inquiry_keywords = [kw for kw in IntentBaselineRules.INQUIRY_KEYWORDS if kw in text_lower]
        if inquiry_keywords:
            confidence = min(0.5 + len(inquiry_keywords) * 0.1, 0.8)
            results.append(("INQUIRY", confidence))
        
        return results
    
    @staticmethod
    def detect_special_labels(text: str, session_context: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        특수 Label 감지 (Baseline 규칙 기반)
        
        주의: Turn 단위 분석을 위해 세션 맥락 사용을 최소화
        - 반복성: 키워드만 감지 (실제 반복 여부는 후속 모듈에서 판단)
        
        Args:
            text: 분석할 텍스트 (해당 Turn만)
            session_context: 세션 맥락 (선택사항, 최소 사용)
        
        Returns:
            [(label, confidence), ...] 리스트
            - label: 특수 Label (REPETITION, UNREASONABLE_DEMAND, IRRELEVANCE)
            - confidence: 신뢰도 (0.0-1.0)
        """
        results = []
        text_lower = text.lower()
        
        # 1. 반복 표현 키워드 감지 (Turn 단위: 키워드만 감지)
        # 실제 반복 여부 판단은 후속 모듈에서 수행
        repetition_count = sum(1 for indicator in IntentBaselineRules.REPETITION_INDICATORS 
                               if indicator in text_lower)
        if repetition_count > 0:
            # 키워드만으로 감지 (세션 맥락 최소 사용)
            confidence = min(0.4 + repetition_count * 0.2, 0.8)  # 최대 0.8로 제한 (후속 모듈에서 실제 판단)
            results.append(("REPETITION", confidence))
        
        # 2. 무리한 요구 감지 (실제로 무리한 요구만, '지금', '당장' 같은 것은 REQUEST로 분류)
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
                confidence = min(0.5 + unreasonable_count * 0.15, 1.0)
                results.append(("UNREASONABLE_DEMAND", confidence))
        
        # 3. 부당성/무관성 감지
        irrelevance_count = sum(1 for kw in IntentBaselineRules.IRRELEVANCE_INDICATORS 
                               if kw in text_lower)
        if irrelevance_count > 0:
            confidence = min(0.3 + irrelevance_count * 0.25, 1.0)
            results.append(("IRRELEVANCE", confidence))
        
        # 4. 낮은 강도 요인도 Special Label 감지에 포함 (신뢰도 가중치 낮게)
        # 예: '정말'과 같은 낮은 강도로 Unreasonable_response를 유발할 수 있는 요인들
        # 이런 요인들은 개별적으로는 낮은 신뢰도를 가지지만, 
        # 다른 요인들과 합산되면 Special Label을 붙이는 계기가 될 수 있음
        
        # 강도 조정: 낮은 강도 키워드는 신뢰도 가중치를 낮게 설정
        # (이미 위의 로직에서 처리되므로 별도 처리 불필요)
        
        return results


