from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ResponseGuide:
    """상담 가이드 데이터 구조입니다."""

    # 1. 상황별 핵심 대응 전략 (summary)
    strategy_title: str
    strategy_description: str

    # 2. 톤 앤 매너
    tone_and_manner: str

    # 3. 필수/금지 키워드
    required_keywords: List[str] = field(default_factory=list)
    prohibited_keywords: List[str] = field(default_factory=list)

    # 4. 상황별 사내 추천 스크립트 데이터
    opening_scripts: List[str] = field(default_factory=list)
    closing_scripts: List[str] = field(default_factory=list)
    solution_scripts: List[str] = field(default_factory=list)

    # 5. 체크포인트
    checkpoints: List[str] = field(default_factory=list)

