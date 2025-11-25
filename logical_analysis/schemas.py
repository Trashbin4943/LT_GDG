# logical_analysis/schemas.py
from ninja import Schema
from typing import List, Dict, Optional
from datetime import datetime

class AnalyzeRequest(Schema):
    session_id: str

class ClassificationResultOut(Schema):
    text: str 
    label: str
    label_type: str
    confidence: float
    probabilities: Dict[str, float]
    action: str
    alert_level: str
    timestamp: Optional[datetime] = None
    created_at: datetime

class SessionSummary(Schema):
    total_sentences: int
    risk_score: int
    highest_alert: str
    primary_intent: str

class AnalysisSessionOut(Schema):
    session_id: str
    created_at: datetime
    summary: SessionSummary
    results: List[ClassificationResultOut]