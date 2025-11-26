from typing import Dict, List

# 1. emtion_analysis.emotion_system의 label_map을 import합니다.
try:
    from emotion_analysis.emotion_system.emotion import label_map as ORIGIN_LABEL_MAP
    EMOTION_LABELS = list(ORIGIN_LABEL_MAP.values())
except ImportError:
    EMOTION_LABELS=[]


# 2. 감정 카테고리 매핑 (Sentiment Map)
SENTIMENT_CATEGORY = {
    "POSITIVE": [
        "감사", "형식적 감사", "진심 어린 감사", "기쁨", "흥분", 
        "자신감", "감동", "호기심", "애정", "요청"
    ],
    "NEGATIVE_HIGH": [ # 고강도 부정 (특별 케어 필요)
        "격분", "분노", "혐오", "좌절", "불안"
    ],
    "NEGATIVE_LOW": [ # 일반 부정
        "불만", "짜증", "경미한 짜증", "실망", "긴장", "혼란", 
        "냉소", "슬픔", "무기력", "피로"
    ],
    "NEUTRAL": ["중립"]
}

# 3. 감정 -> 카테고리 역방향 조회를 위한 헬퍼 함수
def get_sentiment_category(emotion_name: str) -> str:

    if emotion_name not in EMOTION_LABELS:
        pass

    for category, emotions in SENTIMENT_CATEGORY.items():
        if emotion_name in emotions:
            return category
    return "NEUTRAL"