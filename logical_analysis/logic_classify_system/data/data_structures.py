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
    """분류 결과 (확장)"""
    label: str  # 분류된 Label
    label_type: str  # "NORMAL" or "SPECIAL"
    confidence: float  # 신뢰도 (0.0-1.0)
    text: str  # 원본 문장
    probabilities: Optional[Dict[str, float]] = None  # 각 Label별 확률
    timestamp: Optional[datetime] = None
    
    # [NEW] Intensity 정보 (이중 모델 통합)
    # 윤리검증 데이터셋 기반: intensity 범위 0.0 ~ 3.0
    intensity: Optional[float] = None  # 0.0 ~ 3.0 (Intensity Regression 모델 결과)
    intensity_level: Optional[str] = None  # "LOW", "MEDIUM", "HIGH" (3진 분류 모델 결과)
    # 3진 분류 구간: LOW(1.0~1.6), MEDIUM(1.8~2.4), HIGH(2.6~3.0)
    is_immoral: Optional[bool] = None  # intensity > 0.0
    immorality_confidence: Optional[float] = None  # intensity 기반 신뢰도


@dataclass
class PipelineResult:
    """파이프라인 결과"""
    session_id: str
    results: List[ClassificationResult]
    timestamp: Optional[datetime] = None


