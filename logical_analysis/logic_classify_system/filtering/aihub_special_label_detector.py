"""
AI-Hub Special Label 감지기

AI-Hub 모델을 사용한 Special Label 감지
"""
from typing import Optional, List
from datetime import datetime
from logic_classify_system.data.data_structures import SpecialLabelDetectionResult
from logic_classify_system.models.aihub_ethic_model import AIHubEthicModel
from logic_classify_system.config.labels import SpecialLabel
import logging

logger = logging.getLogger(__name__)


class AIHubSpecialLabelDetector:
    """AI-Hub 모델 기반 Special Label 감지기"""
    
    # AI-Hub 모델 라벨 → 프로젝트 Special Label 매핑
    LABEL_MAPPING = {
        "VIOLENCE": SpecialLabel.VIOLENCE_THREAT.value,
        "SEXUAL": SpecialLabel.SEXUAL_HARASSMENT.value,
        "ABUSE": SpecialLabel.PROFANITY.value,  # ABUSE는 PROFANITY로 매핑
        "DISCRIMINATION": SpecialLabel.HATE_SPEECH.value,
        "IMMORAL_NONE": None  # Special Label 아님
    }
    
    # 심각도 매핑
    SEVERITY_MAPPING = {
        SpecialLabel.VIOLENCE_THREAT.value: "HIGH",
        SpecialLabel.SEXUAL_HARASSMENT.value: "HIGH",
        SpecialLabel.HATE_SPEECH.value: "HIGH",
        SpecialLabel.PROFANITY.value: "MEDIUM",
        SpecialLabel.UNREASONABLE_DEMAND.value: "MEDIUM",
        SpecialLabel.REPETITION.value: "LOW"
    }
    
    def __init__(self, aihub_model: Optional[AIHubEthicModel] = None):
        """
        초기화
        
        Args:
            aihub_model: AIHubEthicModel 인스턴스 (None이면 자동 생성하지 않음)
        """
        self.aihub_model = aihub_model
    
    def detect(
        self,
        text: str,
        session_context: Optional[List[str]] = None
    ) -> Optional[SpecialLabelDetectionResult]:
        """
        Special Label 감지 (AI-Hub 모델 사용)
        
        Args:
            text: 분석할 텍스트
            session_context: 세션 맥락 (선택사항)
        
        Returns:
            SpecialLabelDetectionResult 또는 None (감지 실패 시)
        """
        if self.aihub_model is None:
            return None
        
        try:
            # 모델 1: 비도덕 여부 판단
            is_immoral, immoral_confidence = self.aihub_model.predict_immoral(text)
            
            if not is_immoral:
                # 비도덕이 아니면 Special Label 아님
                return None
            
            # 모델 2: 유형 분류
            predicted_type, probs_dict = self.aihub_model.predict_type(text, return_probs=True)
            
            # 프로젝트 Special Label로 매핑
            mapped_label = self.LABEL_MAPPING.get(predicted_type)
            
            if mapped_label is None:
                # IMMORAL_NONE 또는 매핑되지 않은 경우
                return None
            
            # 신뢰도 계산 (모델 1과 모델 2의 평균)
            type_confidence = probs_dict.get(predicted_type, 0.0)
            confidence = (immoral_confidence + type_confidence) / 2.0
            
            # 심각도 결정
            severity = self.SEVERITY_MAPPING.get(mapped_label, "MEDIUM")
            
            return SpecialLabelDetectionResult(
                label=mapped_label,
                confidence=confidence,
                severity=severity,
                detection_method="aihub_model",
                text=text,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"AI-Hub 모델 감지 실패: {e}")
            return None
