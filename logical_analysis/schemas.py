from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

# === 1. API Input Schema (STT 결과 수신용) ===
class SegmentInput(BaseModel):
    """STT 세그먼트 입력 (통일된 양식)"""
    speaker: str  # 'customer' or 'agent' (통일된 양식: customer/agent 사용)
    text: str
    start_time: Optional[float] = None  # 시작 시간 (초 단위, SpeakerSegment와 일치)
    end_time: Optional[float] = None  # 종료 시간 (초 단위, SpeakerSegment와 일치)
    timestamp: Optional[str] = None  # ISO 형식 타임스탬프 (하위 호환성 유지)

class SessionAnalysisRequest(BaseModel):
    """API로 들어오는 전체 세션 데이터"""
    session_id: str
    segments: List[SegmentInput]


# === 2. Internal Mapping Schema (Pipeline -> Service) ===
# 파이프라인의 결과(Dataclass)를 서비스 계층에서 다루기 편하게 정의

class FeatureScores(BaseModel):
    """점수 관련 데이터"""
    profanity_score: float = 0.0
    threat_score: float = 0.0
    unreasonable_demand_score: float = 0.0
    sexual_harassment_score: float = 0.0
    hate_speech_score: float = 0.0
    repetition_keyword_score: float = 0.0
    
    # 추가적인 점수가 들어올 경우를 대비
    model_config = ConfigDict(extra='allow')

class CustomerAnalysisDTO(BaseModel):
    """고객 분석 결과 전송 객체"""
    # 기본 정보
    session_id: str
    turn_index: int
    text: str
    
    # 분석 결과
    is_profanity: bool
    profanity_category: Optional[str] = None
    profanity_method: Optional[str] = None

    label: str
    label_type: str
    classification_confidence: float
    
    # 점수 및 상세 데이터
    feature_scores: FeatureScores
    extracted_features: Dict[str, Any] = Field(default_factory=dict)
