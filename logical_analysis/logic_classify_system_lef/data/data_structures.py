"""
데이터 구조 정의
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ProfanityResult:
    """욕설 감지 결과"""
    is_profanity: bool
    category: Optional[str]  # PROFANITY, VIOLENCE_THREAT, SEXUAL_HARASSMENT, HATE_SPEECH, INSULT
    confidence: float  # 0.0-1.0
    method: Optional[str]  # "korcen" or "baseline"


@dataclass
class ClassificationResult:
    """분류 결과"""
    label: str  # 분류된 Label
    label_type: str  # "NORMAL" or "SPECIAL"
    confidence: float  # 신뢰도 (0.0-1.0)
    text: str  # 원본 문장
    probabilities: Optional[Dict[str, float]] = None  # 각 Label별 확률
    timestamp: Optional[datetime] = None


@dataclass
class PipelineResult:
    """파이프라인 결과"""
    session_id: str
    results: List[ClassificationResult]
    timestamp: Optional[datetime] = None


