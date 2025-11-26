from pydantic import BaseModel, Field
from typing import Optional, Dict

class SolutionRequestDTO(BaseModel):
    session_id: str
    turn_index: int
    text: str
    
    # 1. 감정 정보
    emotion_label: str  # "격분"
    
    # 2. 논리/분류 정보
    logical_label: str      # "COMPLAINT", "PROFANITY"
    logical_type: str       # "NORMAL", "SPECIAL"
    
    # 3. [New] 세부 정보 활용
    profanity_category: Optional[str] = None # "INSULT", "SEXUAL_HARASSMENT", "VIOLENCE_THREAT"
    risk_score: float = 0.0                  # 0.0 ~ 1.0 (종합 위험도)
    
    # 4. [New] 추출된 키워드 (특정 단어 반응형 스크립트용)
    extracted_keywords: Dict[str, list] = Field(default_factory=dict) 
    # 예: {"unreasonable_keywords": ["공짜", "보상"]}