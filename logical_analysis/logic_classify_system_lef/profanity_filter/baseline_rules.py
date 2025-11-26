"""
욕설 필터용 Baseline 규칙

classification_criteria.py의 욕설 관련 규칙만 추출하여 모듈 내부에 포함
모듈 독립성을 위해 외부 파일 의존성 제거
"""

from typing import Tuple, Optional


class ProfanityBaselineRules:
    """욕설 감지용 Baseline 규칙"""
    
    # 직접적 욕설 키워드
    PROFANITY_KEYWORDS = [
        "X팔", "XXX년", "개XX", "XX놈", "XX년", "지랄", "병신", "미친",
        "씨발", "좆", "개새끼", "미친놈", "죽어", "꺼져"
        # 추가 욕설 키워드는 여기에 계속 추가
    ]
    
    # 모욕/조롱 키워드
    INSULT_KEYWORDS = [
        "너 거기 앉아서 뭐 배웠느냐", "고등학교는 나왔느냐", "인격모독",
        "바보", "멍청이", "무식한", "능력없는", "제대로 배우지 못한"
    ]
    
    # 위협 표현 키워드
    THREAT_KEYWORDS = [
        "죽여", "찾아가", "법적 대응", "고소", "복수",
        "죽어", "끝장", "망하", 
    ]
    
    # 성희롱 키워드
    SEXUAL_HARASSMENT_KEYWORDS = [
        "성적인", "음란", "만나자", "연락처", "사적인", "데이트",
        "섹스", "성교", "음란물"
    ]
    
    # 혐오 표현 키워드
    HATE_SPEECH_KEYWORDS = {
        "성_혐오": ["여자는", "남자는", "성차별", "성 고정관념"],
        "연령_차별": ["늙은", "젊은 놈", "아저씨", "아줌마"],
        "인종_지역_혐오": ["지역드립", "전라도", "경상도", "서울 촌놈"],
        "장애인_혐오": ["장애인", "병신", "정신병"],
        "종교_혐오": ["종교", "신앙", "믿음"],
        "정치_혐오": ["정당", "정치인", "좌파", "우파"],
        "직업_혐오": ["직업", "직종"]
    }
    
    @staticmethod
    def detect_profanity(text: str) -> Tuple[bool, Optional[str], float]:
        """
        Baseline 규칙 기반 욕설 감지
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            (is_profanity, category, confidence)
            - is_profanity: 욕설 감지 여부
            - category: 감지된 카테고리 (PROFANITY, VIOLENCE_THREAT, SEXUAL_HARASSMENT, HATE_SPEECH, INSULT)
            - confidence: 신뢰도 (0.0-1.0)
        """
        text_lower = text.lower()
        
        # 1. 직접적 욕설 감지 (최우선)
        profanity_count = sum(1 for kw in ProfanityBaselineRules.PROFANITY_KEYWORDS 
                             if kw in text_lower)
        if profanity_count > 0:
            return True, "PROFANITY", min(0.5 + profanity_count * 0.15, 1.0)
        
        # 2. 위협 표현 감지 (CRITICAL)
        threat_count = sum(1 for kw in ProfanityBaselineRules.THREAT_KEYWORDS 
                          if kw in text_lower)
        if threat_count > 0:
            return True, "VIOLENCE_THREAT", min(0.7 + threat_count * 0.15, 1.0)
        
        # 3. 성희롱 감지 (CRITICAL)
        sexual_count = sum(1 for kw in ProfanityBaselineRules.SEXUAL_HARASSMENT_KEYWORDS 
                          if kw in text_lower)
        if sexual_count > 0:
            return True, "SEXUAL_HARASSMENT", min(0.6 + sexual_count * 0.2, 1.0)
        
        # 4. 혐오 표현 감지
        for category, keywords in ProfanityBaselineRules.HATE_SPEECH_KEYWORDS.items():
            hate_count = sum(1 for kw in keywords if kw in text_lower)
            if hate_count > 0:
                return True, "HATE_SPEECH", min(0.6 + hate_count * 0.15, 1.0)
        
        # 5. 모욕/조롱 감지
        insult_count = sum(1 for kw in ProfanityBaselineRules.INSULT_KEYWORDS 
                         if kw in text_lower)
        if insult_count > 0:
            return True, "INSULT", min(0.4 + insult_count * 0.2, 1.0)
        
        return False, None, 0.0


