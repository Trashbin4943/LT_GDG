"""
의도 분류기

Special Label 및 Normal Label 분류, 파이프라인 모드에 따른 분기 처리
"""
from typing import Optional, List
from datetime import datetime
import logging
from logic_classify_system.data.data_structures import ClassificationResult
from logic_classify_system.config.labels import (
    PipelineMode,
    LabelType,
    SpecialLabel,
    NormalLabel
)
from logic_classify_system.filtering.special_label_filter import SpecialLabelFilter
from logic_classify_system.intent_classifier.baseline_rules import IntentBaselineRules
from logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
import logging

logger = logging.getLogger(__name__)


class IntentPredictor:
    """의도 분류기"""
    
    # Korcen 힌트 → Special Label 매핑
    KORCEN_HINT_MAPPING = {
        "PROFANITY_DETECTED": SpecialLabel.PROFANITY.value,
        "SEXUAL_DETECTED": SpecialLabel.SEXUAL_HARASSMENT.value,
        "HATE_DETECTED": SpecialLabel.HATE_SPEECH.value,
        "VIOLENCE_THREAT": SpecialLabel.VIOLENCE_THREAT.value
    }
    
    def __init__(
        self,
        mode: PipelineMode = PipelineMode.default(),
        special_label_filter: Optional[SpecialLabelFilter] = None,
        profanity_detector: Optional[ProfanityDetector] = None
    ):
        """
        초기화
        
        Args:
            mode: 파이프라인 모드
            special_label_filter: SpecialLabelFilter 인스턴스
            profanity_detector: ProfanityDetector 인스턴스
        """
        self.mode = mode
        self.special_label_filter = special_label_filter
        self.profanity_detector = profanity_detector or ProfanityDetector()
        self.intent_baseline = IntentBaselineRules()
    
    def predict(
        self,
        text: str,
        profanity_detected: bool = False,
        session_context: Optional[List[str]] = None,
        profanity_category: Optional[str] = None,
        profanity_confidence: float = 0.0
    ) -> ClassificationResult:
        """
        의도 분류 (파이프라인 모드에 따른 분기)
        
        Args:
            text: 분석할 텍스트
            profanity_detected: 욕설 감지 여부
            session_context: 세션 맥락
            profanity_category: Korcen 힌트
            profanity_confidence: 욕설 감지 신뢰도
        
        Returns:
            ClassificationResult
        """
        if self.mode == PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL:
            return self._predict_fast_classify_then_conditional_detail(
                text, profanity_detected, session_context,
                profanity_category, profanity_confidence
            )
        elif self.mode == PipelineMode.CLASSIFY_BOTH_ALWAYS:
            return self._predict_classify_both_always(
                text, profanity_detected, session_context,
                profanity_category, profanity_confidence
            )
        elif self.mode == PipelineMode.DETAIL_FIRST_THEN_VERIFY:
            return self._predict_detail_first_then_verify(
                text, profanity_detected, session_context,
                profanity_category, profanity_confidence
            )
        else:
            # 기본값: INQUIRY
            return self._default_result(text)
    
    def _predict_fast_classify_then_conditional_detail(
        self,
        text: str,
        profanity_detected: bool,
        session_context: Optional[List[str]],
        profanity_category: Optional[str],
        profanity_confidence: float
    ) -> ClassificationResult:
        """모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL"""
        # Korcen 힌트 확인
        if profanity_detected and profanity_category:
            # Korcen 힌트 → Special Label 변환
            label = self.KORCEN_HINT_MAPPING.get(profanity_category)
            
            if label:
                # 조건 확인: 모델 사용 필요?
                use_model = (
                    profanity_confidence < 0.7 or  # 신뢰도 낮음
                    profanity_category == "PROFANITY_DETECTED"  # 특정 Label 추가 검증
                )
                
                if use_model and self.special_label_filter:
                    # SpecialLabelFilter.detect() (모델 기반)
                    detection = self.special_label_filter.detect(text, session_context)
                    if detection:
                        return ClassificationResult(
                            label=detection.label,
                            label_type=LabelType.SPECIAL.value,
                            confidence=detection.confidence,
                            text=text,
                            timestamp=datetime.now()
                        )
                
                # Korcen 힌트 기반 Label 반환
                return ClassificationResult(
                    label=label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=profanity_confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # profanity_detected == False
        # SpecialLabelFilter.detect() (모델/Baseline)
        if self.special_label_filter:
            detection = self.special_label_filter.detect(text, session_context)
            if detection:
                return ClassificationResult(
                    label=detection.label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=detection.confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # 미감지 → Normal Label 분류
        return self._classify_normal_label(text)
    
    def _predict_classify_both_always(
        self,
        text: str,
        profanity_detected: bool,
        session_context: Optional[List[str]],
        profanity_category: Optional[str],
        profanity_confidence: float
    ) -> ClassificationResult:
        """모드 2: CLASSIFY_BOTH_ALWAYS"""
        # SpecialLabelFilter.detect() (항상 실행)
        if self.special_label_filter:
            detection = self.special_label_filter.detect(text, session_context)
            if detection:
                return ClassificationResult(
                    label=detection.label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=detection.confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # 미감지
        if profanity_detected and profanity_category:
            # Korcen 힌트 → Special Label 변환
            label = self.KORCEN_HINT_MAPPING.get(profanity_category)
            if label:
                return ClassificationResult(
                    label=label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=profanity_confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # Normal Label 분류
        return self._classify_normal_label(text)
    
    def _predict_detail_first_then_verify(
        self,
        text: str,
        profanity_detected: bool,
        session_context: Optional[List[str]],
        profanity_category: Optional[str],
        profanity_confidence: float
    ) -> ClassificationResult:
        """모드 3: DETAIL_FIRST_THEN_VERIFY"""
        # SpecialLabelFilter.detect() (우선 실행)
        if self.special_label_filter:
            detection = self.special_label_filter.detect(text, session_context)
            if detection:
                # Special Label 감지됨
                confidence = detection.confidence
                
                if profanity_detected and profanity_category:
                    # Korcen 힌트와 비교
                    korcen_label = self.KORCEN_HINT_MAPPING.get(profanity_category)
                    
                    if korcen_label == detection.label:
                        # 일치 → 신뢰도 상향 조정
                        confidence = min(1.0, confidence + 0.1)
                    else:
                        # 불일치 → 신뢰도 하향 조정
                        confidence = max(0.0, confidence - 0.1)
                
                return ClassificationResult(
                    label=detection.label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # 미감지
        if profanity_detected and profanity_category:
            # Korcen 힌트 → Special Label 변환
            label = self.KORCEN_HINT_MAPPING.get(profanity_category)
            if label:
                return ClassificationResult(
                    label=label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=profanity_confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
        # Normal Label 분류
        return self._classify_normal_label(text)
    
    def _classify_normal_label(self, text: str) -> ClassificationResult:
        """Normal Label 분류 (기본값: INQUIRY)"""
        # 향후 KoSentenceBERT 또는 다른 모델로 확장 가능
        # 현재는 기본값 반환
        return ClassificationResult(
            label=NormalLabel.INQUIRY.value,
            label_type=LabelType.NORMAL.value,
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
    
    def _default_result(self, text: str) -> ClassificationResult:
        """기본 결과 (에러 처리)"""
        return ClassificationResult(
            label=NormalLabel.INQUIRY.value,
            label_type=LabelType.UNKNOWN.value,
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
