"""
평가 결과 데이터 구조
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class EvaluationResult:
    """평가 결과"""
    label: str                         # Normal Label
    score: float                       # 종합 점수 (0-100)
    criteria_scores: Dict[str, float]  # 항목별 점수
    feedback: str                      # 피드백 메시지
    recommendations: List[str]         # 개선 제안
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None

