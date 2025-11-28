from typing import List, Dict, Optional, Any
from ninja import Schema
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# === 1. API Input Schema ===
class SegmentInput(Schema):
    id: Optional[int] = None
    speaker: str
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    timestamp: Optional[str] = None

class SessionAnalysisRequest(Schema):
    """분석 요청 전체 바디"""
    session_id: str
    segments: List[SegmentInput]
    
# === 2. API Output Schema ===

class FeatureScores(Schema):
    """상세 점수"""
    profanity_score: float = 0.0
    threat_score: float = 0.0
    unreasonable_demand_score: float = 0.0
    sexual_harassment_score: float = 0.0
    hate_speech_score: float = 0.0
    repetition_keyword_score: float = 0.0
    model_config = ConfigDict(extra='allow')

class AnalysisResultItemSchema(Schema):
    text: str
    label: str
    label_type: str
    classification_confidence: float
    probabilities: Optional[Dict[str, float]] = None
    
    score_risk: float = 0.0
    is_profanity: bool = False

    profanity_category: Optional[str] = None
    profanity_method: Optional[str] = None

    intensity: Optional[float] = Field(None, description= "intensity level")
    intensity_level: Optional[str] = Field(None, description="LOW, MEDIUM, HIGH")
    is_immoral: Optional[bool] = Field(None, description="비도덕성 여부")
    immorality_confidence: Optional[float] = Field(None, description="도덕성 검증 신뢰도")

    feature_scores: Optional[FeatureScores] = None
    extracted_features: Dict[str, Any] = Field(default_factory=dict)
    
    timestamp: Optional[float] = None
    created_at: Optional[datetime] = None

class AnalysisSummarySchema(Schema):
    total_sentences: int
    risk_score: float
    highest_alert: str
    primary_intent: str

class CustomerAnalysisResponseSchema(Schema):
    session_id: str
    created_at: Optional[datetime] = None
    summary: AnalysisSummarySchema
    results: List[AnalysisResultItemSchema]