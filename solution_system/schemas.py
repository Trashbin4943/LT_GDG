from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SolutionRequestDTO(BaseModel):
    """
    [Input] 솔루션 생성을 위한 요청 데이터
    """
    # 식별자: 이 두 정보로 SpeakerSegment를 찾습니다.
    session_id: str
    turn_index: int
    
    text: str 
    
    # 분석 결과 데이터
    emotion_label: str
    logical_label: str
    logical_type: str
    
    risk_score: float = 0.0
    profanity_category: Optional[str] = None
    
    extracted_keywords: Dict[str, List[str]] = Field(default_factory=dict)


class SolutionResponseDTO(BaseModel):
    """
    [Output] 생성된 솔루션 결과 반환
    """
    session_id: str
    turn_index: int
    
    # 생성된 가이드 내용
    strategy_title: str
    strategy_description: str
    tone_and_manner: str
    
    required_keywords: List[str]
    prohibited_keywords: List[str]
    solution_scripts: List[str]
    checkpoints: List[str]
    
    created_at: datetime