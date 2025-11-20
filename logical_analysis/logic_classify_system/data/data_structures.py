"""
데이터 구조 정의

프로세스 전반에서 사용되는 표준화된 데이터 구조
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class ProfanityResult:
    """욕설 감지 결과"""
    is_profanity: bool
    category: str  # Korcen 힌트 또는 Baseline Label
    confidence: float
    method: str  # "korcen" 또는 "baseline"
    text: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class ClassificationResult:
    """분류 결과"""
    label: str
    label_type: str  # "SPECIAL" 또는 "NORMAL"
    confidence: float
    text: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SpecialLabelDetectionResult:
    """Special Label 감지 결과"""
    label: str
    confidence: float
    severity: str  # "LOW", "MEDIUM", "HIGH"
    detection_method: str  # "aihub_model" 또는 "baseline"
    text: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class FilteringResult:
    """필터링 결과"""
    label: str
    severity: str
    action: str  # "ALERT", "BLOCK", "LOG"
    alert_level: str
    text: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    """평가 결과 (Normal Label)"""
    label: str
    score: float  # 0-100
    criteria_scores: Dict[str, float]  # 적절성, 명확성, 맥락 일치, 응답 품질
    feedback: str
    text: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class RouterResult:
    """라우팅 결과"""
    route_type: str  # "EVALUATION", "FILTERING", "UNKNOWN"
    result: Any  # EvaluationResult 또는 FilteringResult
    classification_result: ClassificationResult


@dataclass
class PipelineResult:
    """파이프라인 전체 처리 결과"""
    results: List[ClassificationResult]
    session_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
