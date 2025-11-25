"""
Label 정의

기존 labels.py에서 복사
"""

from enum import Enum


class NormalLabel(Enum):
    """Normal Label 정의"""
    INQUIRY = "INQUIRY"
    COMPLAINT = "COMPLAINT"
    REQUEST = "REQUEST"
    CLARIFICATION = "CLARIFICATION"
    CONFIRMATION = "CONFIRMATION"
    CLOSING = "CLOSING"


class SpecialLabel(Enum):
    """특수 Label 정의"""
    VIOLENCE_THREAT = "VIOLENCE_THREAT"
    SEXUAL_HARASSMENT = "SEXUAL_HARASSMENT"
    PROFANITY = "PROFANITY"
    HATE_SPEECH = "HATE_SPEECH"
    UNREASONABLE_DEMAND = "UNREASONABLE_DEMAND"
    REPETITION = "REPETITION"


# Label 타입 구분
NORMAL_LABELS = [label.value for label in NormalLabel]
SPECIAL_LABELS = [label.value for label in SpecialLabel]



