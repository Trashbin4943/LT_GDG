"""
라벨 정의 및 파이프라인 모드
"""

from enum import Enum


class NormalLabel(Enum):
    """Normal Label 정의 (HEAD: 순서 유지)"""
    INQUIRY = "INQUIRY"
    COMPLAINT = "COMPLAINT"
    REQUEST = "REQUEST"
    CLARIFICATION = "CLARIFICATION"
    CONFIRMATION = "CONFIRMATION"
    CLOSING = "CLOSING"
    
    @classmethod
    def values(cls):
        """모든 Normal Label 값 리스트 반환 (logic: 추가)"""
        return [label.value for label in cls]
    
    @classmethod
    def from_string(cls, label_str: str):
        """문자열로부터 NormalLabel 반환 (logic: 추가)"""
        try:
            return cls(label_str)
        except ValueError:
            return None


class SpecialLabel(Enum):
    """특수 Label 정의"""
    VIOLENCE_THREAT = "VIOLENCE_THREAT"
    SEXUAL_HARASSMENT = "SEXUAL_HARASSMENT"
    PROFANITY = "PROFANITY"
    HATE_SPEECH = "HATE_SPEECH"
    UNREASONABLE_DEMAND = "UNREASONABLE_DEMAND"
    REPETITION = "REPETITION"
    
    @classmethod
    def values(cls):
        """모든 Special Label 값 리스트 반환 (logic: 추가)"""
        return [label.value for label in cls]
    
    @classmethod
    def from_string(cls, label_str: str):
        """문자열로부터 SpecialLabel 반환 (logic: 추가)"""
        try:
            return cls(label_str)
        except ValueError:
            return None


# Label 타입 구분 (HEAD: 유지)
NORMAL_LABELS = [label.value for label in NormalLabel]
SPECIAL_LABELS = [label.value for label in SpecialLabel]


class LabelType(Enum):
    """라벨 타입 (logic: 추가)"""
    SPECIAL = "SPECIAL"
    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"
    
    @classmethod
    def from_string(cls, label_type_str: str):
        """문자열로부터 LabelType 반환"""
        try:
            return cls(label_type_str)
        except ValueError:
            return None


class PipelineMode(Enum):
    """파이프라인 작동 모드 (logic: 추가)"""
    FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL = "FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL"
    CLASSIFY_BOTH_ALWAYS = "CLASSIFY_BOTH_ALWAYS"
    DETAIL_FIRST_THEN_VERIFY = "DETAIL_FIRST_THEN_VERIFY"
    
    @classmethod
    def default(cls):
        return cls.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL
