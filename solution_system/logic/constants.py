# logical_analysis/solution_system/logic/constants.py

class SentimentType:
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"

# [변경] 단순화된 감정 라벨('긍정', '부정', '중립')을 내부 상수로 매핑
SENTIMENT_MAP = {
    "긍정": SentimentType.POSITIVE,
    "부정": SentimentType.NEGATIVE,
    "중립": SentimentType.NEUTRAL
}

def get_sentiment_category(emotion_label: str) -> str:
    """단순화된 감정 라벨을 받아 내부 상수(POSITIVE 등)로 변환"""
    return SENTIMENT_MAP.get(emotion_label, SentimentType.NEUTRAL)

class IntensityLevel:
    HIGH = "HIGH"       # 격앙 (즉각적 조치/진정 필요)
    MEDIUM = "MEDIUM"   # 일반
    LOW = "LOW"         # 차분함

class LogicalType:
    SPECIAL = "SPECIAL"  # 특수 상황 (위험)
    NORMAL = "NORMAL"    # 일반 상황