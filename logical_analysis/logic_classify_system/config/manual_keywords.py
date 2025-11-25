"""
매뉴얼 키워드 정의

감정 라벨 + CAR (Customer Analysis Result) 조합에 따른 매뉴얼 키워드 정의
Keyword 기반 매뉴얼 준수 평가를 위한 기준
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class EmotionLabel(Enum):
    """감정 라벨 정의 (예시 - 실제 감정 분류 시스템에 맞게 조정 필요)"""
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    ANGRY = "ANGRY"
    FRUSTRATED = "FRUSTRATED"
    SATISFIED = "SATISFIED"
    CONFUSED = "CONFUSED"
    # 추가 감정 라벨 필요 시 확장


@dataclass
class ManualKeywords:
    """매뉴얼 키워드 정의"""
    # 인사 관련 키워드
    greeting_keywords: List[str] = field(default_factory=list)  # 시작 인사
    closing_keywords: List[str] = field(default_factory=list)  # 마무리 인사
    
    # 상황 대응 필수 키워드 (작은 조각 단위)
    required_keywords: List[str] = field(default_factory=list)  # 필수 포함 키워드
    optional_keywords: List[str] = field(default_factory=list)  # 권장 포함 키워드
    prohibited_keywords: List[str] = field(default_factory=list)  # 금지 키워드
    
    # 상황별 응대 표현 (단어/구 단위)
    response_phrases: List[str] = field(default_factory=list)  # 응대 표현
    empathy_phrases: List[str] = field(default_factory=list)  # 공감 표현
    solution_phrases: List[str] = field(default_factory=list)  # 해결 방안 표현


class ManualKeywordConfig:
    """매뉴얼 키워드 설정 클래스"""
    
    def __init__(self):
        """매뉴얼 키워드 초기화"""
        # 감정 라벨 + CAR 조합별 매뉴얼 키워드 매핑
        # Key: (emotion_label, customer_label), Value: ManualKeywords
        self.manual_map: Dict[tuple[str, str], ManualKeywords] = {}
        self._initialize_default_keywords()
    
    def _initialize_default_keywords(self):
        """기본 매뉴얼 키워드 초기화"""
        
        # ===== 일반 인사 키워드 (모든 상황 공통) =====
        common_greeting = ["안녕하세요", "안녕", "안녕하십니까", "안녕하시나요", "안부"]
        common_closing = [
            "감사합니다", "감사", "감사드립니다", "감사드려요",
            "이상입니다", "끝내겠습니다", "종료", "마무리",
            "추가 문의", "추가 문의사항"
        ]
        
        # ===== 감정 라벨별 기본 키워드 =====
        
        # NEUTRAL + Normal Label 조합
        for normal_label in ["INQUIRY", "COMPLAINT", "REQUEST", "CLARIFICATION", "CONFIRMATION", "CLOSING"]:
            key = ("NEUTRAL", normal_label)
            self.manual_map[key] = ManualKeywords(
                greeting_keywords=common_greeting,
                closing_keywords=common_closing,
                required_keywords=["안내", "확인", "처리", "도움"],
                optional_keywords=["문의", "상담", "진행", "제출"],
                response_phrases=["안내드리겠습니다", "확인해보겠습니다", "처리해드리겠습니다"],
                empathy_phrases=[],
                solution_phrases=["도와드리겠습니다", "진행해드리겠습니다"]
            )
        
        # NEGATIVE/ANGRY + Normal Label 조합 (불만/요청 등)
        for normal_label in ["COMPLAINT", "REQUEST"]:
            for emotion in ["NEGATIVE", "ANGRY", "FRUSTRATED"]:
                key = (emotion, normal_label)
                self.manual_map[key] = ManualKeywords(
                    greeting_keywords=common_greeting,
                    closing_keywords=common_closing,
                    required_keywords=["죄송", "불편", "이해", "처리", "해결"],
                    optional_keywords=["양해", "반영", "개선", "조치"],
                    response_phrases=["죄송합니다", "불편을 드려 죄송합니다", "이해해주셔서 감사합니다"],
                    empathy_phrases=[
                        "불편을 드려 죄송합니다",
                        "이해하시는 마음 감사드립니다",
                        "불편하셨을 것 같습니다",
                        "양해 부탁드립니다"
                    ],
                    solution_phrases=[
                        "최선을 다해 해결하겠습니다",
                        "처리해드리겠습니다",
                        "개선하겠습니다",
                        "조치하겠습니다"
                    ]
                )
        
        # NEGATIVE/ANGRY + Special Label 조합 (특수 상황 대응)
        for special_label in ["PROFANITY", "VIOLENCE_THREAT", "HATE_SPEECH", "UNREASONABLE_DEMAND"]:
            for emotion in ["NEGATIVE", "ANGRY", "FRUSTRATED"]:
                key = (emotion, special_label)
                self.manual_map[key] = ManualKeywords(
                    greeting_keywords=common_greeting,
                    closing_keywords=common_closing,
                    required_keywords=["정중", "이해", "협조", "대화", "상담"],
                    optional_keywords=["양해", "원활", "건설적"],
                    prohibited_keywords=["욕", "비하", "모욕", "무시"],  # 사용 금지
                    response_phrases=[
                        "정중히 안내드리겠습니다",
                        "원활한 소통을 위해",
                        "건설적인 대화를 위해"
                    ],
                    empathy_phrases=[
                        "이해해주시길 부탁드립니다",
                        "양해 부탁드립니다",
                        "협조 부탁드립니다"
                    ],
                    solution_phrases=[
                        "상담 진행해드리겠습니다",
                        "도와드리겠습니다",
                        "해결 방안 모색하겠습니다"
                    ]
                )
        
        # CONFUSED + Normal Label 조합 (명확화 요청)
        for normal_label in ["CLARIFICATION", "CONFIRMATION", "INQUIRY"]:
            key = ("CONFUSED", normal_label)
            self.manual_map[key] = ManualKeywords(
                greeting_keywords=common_greeting,
                closing_keywords=common_closing,
                required_keywords=["명확", "확인", "설명", "안내"],
                optional_keywords=["추가", "상세", "정리", "요약"],
                response_phrases=[
                    "명확히 안내드리겠습니다",
                    "확인해드리겠습니다",
                    "설명드리겠습니다"
                ],
                empathy_phrases=[],
                solution_phrases=["정리해드리겠습니다", "요약해드리겠습니다"]
            )
        
        # POSITIVE/SATISFIED + Normal Label 조합 (긍정적 응대)
        for normal_label in ["CLOSING", "CONFIRMATION"]:
            for emotion in ["POSITIVE", "SATISFIED"]:
                key = (emotion, normal_label)
                self.manual_map[key] = ManualKeywords(
                    greeting_keywords=common_greeting,
                    closing_keywords=common_closing + ["다음에도", "항상", "기대"],
                    required_keywords=["감사", "도움", "만족"],
                    optional_keywords=["추천", "기억", "방문"],
                    response_phrases=["감사드립니다", "도움드려 기쁩니다", "만족스러우셨다면"],
                    empathy_phrases=[],
                    solution_phrases=["다음에도 도와드리겠습니다"]
                )
    
    def get_keywords(
        self,
        emotion_label: str,
        customer_label: str
    ) -> ManualKeywords:
        """
        감정 라벨 + CAR 조합에 따른 매뉴얼 키워드 반환
        
        Args:
            emotion_label: 감정 라벨 (예: "NEUTRAL", "NEGATIVE", "ANGRY")
            customer_label: 손님 발화 Label (예: "INQUIRY", "COMPLAINT", "PROFANITY")
        
        Returns:
            ManualKeywords: 해당 조합의 매뉴얼 키워드
        """
        key = (emotion_label, customer_label)
        
        # 정확한 조합이 없으면 기본값 반환
        if key not in self.manual_map:
            # 기본 매뉴얼 (일반적인 인사만)
            return ManualKeywords(
                greeting_keywords=["안녕하세요", "안녕"],
                closing_keywords=["감사합니다", "이상입니다"]
            )
        
        return self.manual_map[key]
    
    def get_greeting_keywords(self) -> List[str]:
        """공통 시작 인사 키워드 반환"""
        return ["안녕하세요", "안녕", "안녕하십니까", "안녕하시나요"]
    
    def get_closing_keywords(self) -> List[str]:
        """공통 마무리 인사 키워드 반환"""
        return ["감사합니다", "감사", "감사드립니다", "이상입니다", "끝내겠습니다"]


# 전역 매뉴얼 키워드 설정 인스턴스
manual_keyword_config = ManualKeywordConfig()

