"""
세션 공통 유틸리티 함수

검증 함수 및 공통 로직
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_score(score: float, field_name: str) -> float:
    """
    점수 범위 검증 및 클리핑 (0.0-1.0)
    
    Args:
        score: 검증할 점수
        field_name: 필드 이름 (로깅용)
    
    Returns:
        검증된 점수 (0.0 ~ 1.0)
    """
    if score is None:
        return 0.0
    validated = max(0.0, min(1.0, float(score)))
    if validated != score:
        logger.warning(f"{field_name} 점수 범위 조정: {score} → {validated}")
    return validated


def validate_text(text: str, max_length: int = 10000) -> str:
    """
    텍스트 검증
    
    Args:
        text: 검증할 텍스트
        max_length: 최대 길이
    
    Returns:
        검증된 텍스트
    """
    if not text:
        return ""
    if len(text) > max_length:
        logger.warning(f"텍스트 길이 초과: {len(text)} > {max_length}, 잘림")
        return text[:max_length]
    return text


def validate_label(label: str, default: str = "INQUIRY") -> str:
    """
    라벨 검증
    
    Args:
        label: 검증할 라벨
        default: 기본값
    
    Returns:
        검증된 라벨
    """
    if not label or not label.strip():
        logger.warning(f"라벨이 비어있음, 기본값 사용: {default}")
        return default
    return label.strip()


def validate_label_type(label: str, label_type: str) -> str:
    """
    라벨과 라벨 타입 일관성 검증
    
    Args:
        label: 라벨
        label_type: 라벨 타입
    
    Returns:
        검증된 라벨 타입
    """
    NORMAL_LABELS = ["INQUIRY", "COMPLAINT", "REQUEST", "CLARIFICATION", "CONFIRMATION", "CLOSING"]
    SPECIAL_LABELS = ["PROFANITY", "VIOLENCE_THREAT", "SEXUAL_HARASSMENT", "HATE_SPEECH", "UNREASONABLE_DEMAND", "REPETITION"]
    
    if label_type == "NORMAL" and label not in NORMAL_LABELS:
        logger.warning(f"라벨 타입 불일치: label={label}, label_type={label_type}, NORMAL로 수정")
        return "NORMAL"
    elif label_type == "SPECIAL" and label not in SPECIAL_LABELS:
        logger.warning(f"라벨 타입 불일치: label={label}, label_type={label_type}, SPECIAL로 수정")
        return "SPECIAL"
    
    return label_type

