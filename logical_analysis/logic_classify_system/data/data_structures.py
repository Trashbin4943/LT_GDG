"""
Turn 단위 분석 데이터 구조 정의

프로세스 전반에서 사용되는 표준화된 데이터 구조
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class ProfanityResult:
    """욕설 감지 결과"""
    is_profanity: bool
    category: Optional[str]  # PROFANITY, VIOLENCE_THREAT, SEXUAL_HARASSMENT, HATE_SPEECH, INSULT (HEAD: Optional 유지)
    confidence: float  # 0.0-1.0
    method: Optional[str]  # "korcen" or "baseline" (HEAD: Optional 유지)
    text: Optional[str] = None  # logic: 추가
    timestamp: Optional[datetime] = None  # logic: 추가


@dataclass
class ClassificationResult:
    """분류 결과 (확장)"""
    label: str  # 분류된 Label
    label_type: str  # "NORMAL" or "SPECIAL"
    confidence: float  # 신뢰도 (0.0-1.0)
    text: str  # 원본 문장
    probabilities: Optional[Dict[str, float]] = None  # 각 Label별 확률 (HEAD: 유지)
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None  # logic: 추가
    
    # [NEW] Intensity 정보 (이중 모델 통합)
    # 윤리검증 데이터셋 기반: intensity 범위 0.0 ~ 3.0
    intensity: Optional[float] = None  # 0.0 ~ 3.0 (Intensity Regression 모델 결과)
    intensity_level: Optional[str] = None  # "LOW", "MEDIUM", "HIGH" (3진 분류 모델 결과)
    # 3진 분류 구간: LOW(1.0~1.6), MEDIUM(1.8~2.4), HIGH(2.6~3.0)
    is_immoral: Optional[bool] = None  # intensity > 0.0
    immorality_confidence: Optional[float] = None  # intensity 기반 신뢰도


@dataclass
class SpecialLabelDetectionResult:
    """Special Label 감지 결과 (logic 브랜치)"""
    label: str
    confidence: float
    severity: str  # "LOW", "MEDIUM", "HIGH"
    detection_method: str  # "aihub_model" 또는 "baseline"
    text: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class FilteringResult:
    """필터링 결과 (logic 브랜치)"""
    label: str
    severity: str
    action: str  # "ALERT", "BLOCK", "LOG"
    alert_level: str
    text: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    """평가 결과 (Normal Label) (logic 브랜치)"""
    label: str
    score: float  # 0-100
    criteria_scores: Dict[str, float]  # 적절성, 명확성, 맥락 일치, 응답 품질
    feedback: str
    text: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class RouterResult:
    """라우팅 결과 (logic 브랜치)"""
    route_type: str  # "EVALUATION", "FILTERING", "UNKNOWN"
    result: Any  # EvaluationResult 또는 FilteringResult
    classification_result: ClassificationResult


@dataclass
class CustomerAnalysisResult:
    """고객 발화 분석 결과 (테스트용)"""
    session_id: str
    turn_index: int
    text: str
    timestamp: datetime
    profanity_result: ProfanityResult
    classification_result: ClassificationResult
    feature_scores: Dict[str, float]
    extracted_features: Dict[str, Any]


@dataclass
class AgentAnalysisResult:
    """상담원 발화 분석 결과 (테스트용)"""
    session_id: str
    turn_index: int
    text: str
    timestamp: datetime
    corresponding_customer_label: str
    emotion_label: Optional[str] = None
    manual_compliance_score: float = 0.0
    compliance_details: Dict[str, Any] = None
    feature_scores: Dict[str, float] = None
    extracted_features: Dict[str, Any] = None


@dataclass
class PipelineResult:
    """파이프라인 결과"""
    session_id: str  # HEAD: 순서 유지
    results: List[ClassificationResult]
    timestamp: Optional[datetime] = None  # HEAD: Optional 유지
    metadata: Optional[Dict[str, Any]] = None  # logic: 추가
