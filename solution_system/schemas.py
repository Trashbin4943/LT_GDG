from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from ninja import Schema

class SolutionRequestDTO(Schema):
    segment_id: int
    session_id: str
    turn_index: int
    text: str
    
    # [핵심 4축 데이터]
    emotion_label: str = Field(..., description="'긍정', '중립', '부정'")
    logical_label: str
    logical_type: str = Field(..., description="'NORMAL' or 'SPECIAL'")
    intensity_level: str = Field("LOW", description="'LOW', 'MEDIUM', 'HIGH'")
    is_immoral: bool = Field(False, description="비도덕성 여부")
    
    # 부가 정보
    risk_score: float = 0.0
    profanity_category: Optional[str] = None
    extracted_keywords: Dict[str, Any] = Field(default_factory=dict)


class SolutionResponseDTO(BaseModel):
    strategy_title: str = Field(..., description="대응 전략 제목 (예: 격앙된 고객 진정 유도)")
    strategy_description: str = Field(..., description="상세 대응 가이드 (예: 고객의 말을 끊지 말고...)")

    tone_and_manner: str = Field(..., description="권장 목소리 톤 및 태도 (예: 차분하고 낮은 톤)")

    solution_scripts: List[str] = Field(default_factory=list, description="실제 응대 스크립트 리스트")
    checkpoints: List[str] = Field(default_factory=list, description="상담 시 유의사항 리스트")