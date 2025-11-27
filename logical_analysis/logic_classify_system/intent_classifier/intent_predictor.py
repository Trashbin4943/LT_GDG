"""
발화 의도 예측 통합 인터페이스

Baseline 규칙 + KoSentenceBERT를 통합하여 발화 의도를 분류 (HEAD 기반)
Special Label 및 Normal Label 분류, 파이프라인 모드에 따른 분기 처리 (logic 기능 통합)
"""

from typing import Optional, List
from datetime import datetime
import logging

from .baseline_rules import IntentBaselineRules
from ..data.data_structures import ClassificationResult
from ..config.labels import (
    NORMAL_LABELS,
    SPECIAL_LABELS,
    PipelineMode,
    LabelType,
    SpecialLabel,
    NormalLabel
)

# logic: 선택적 import
try:
    from ..filtering.special_label_filter import SpecialLabelFilter
    from ..profanity_filter.profanity_detector import ProfanityDetector
except ImportError:
    SpecialLabelFilter = None
    ProfanityDetector = None

logger = logging.getLogger(__name__)


class IntentPredictor:
    """발화 의도 예측기 (HEAD 기반 + logic 기능 통합)"""
    
    # Korcen 힌트 → Special Label 매핑 (logic: 추가)
    KORCEN_HINT_MAPPING = {
        "PROFANITY_DETECTED": SpecialLabel.PROFANITY.value,
        "SEXUAL_DETECTED": SpecialLabel.SEXUAL_HARASSMENT.value,
        "HATE_DETECTED": SpecialLabel.HATE_SPEECH.value,
        "VIOLENCE_THREAT": SpecialLabel.VIOLENCE_THREAT.value
    }
    
    def __init__(
        self,
        mode: Optional[PipelineMode] = None,
        special_label_filter: Optional[SpecialLabelFilter] = None,
        profanity_detector: Optional[ProfanityDetector] = None
    ):
        """
        발화 의도 예측기 초기화
        
        Args:
            mode: 파이프라인 모드 (logic: 추가)
            special_label_filter: SpecialLabelFilter 인스턴스 (logic: 추가)
            profanity_detector: ProfanityDetector 인스턴스 (logic: 추가)
        """
        # HEAD: 기본 구조 유지
        # KoSentenceBERT 분류기 (향후 구현)
        # from intent_classifier.kosentbert_classifier import KoSentenceBERTClassifier
        # self.classifier = KoSentenceBERTClassifier()
        self.classifier = None
        
        # Baseline 규칙은 모듈 내부에 포함
        self.baseline_rules = IntentBaselineRules()
        
        # logic: 추가 기능
        self.mode = mode or PipelineMode.default()
        self.special_label_filter = special_label_filter
        self.profanity_detector = profanity_detector
    
    def predict(
        self,
        text: str,
        profanity_detected: bool = False,
        session_context: Optional[List[str]] = None,
        profanity_category: Optional[str] = None,
        profanity_confidence: float = 0.0
    ) -> ClassificationResult:
        """
        발화 의도 예측 (통합) (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            text: 분석할 문장
            profanity_detected: 1차 필터링에서 욕설 감지 여부
            session_context: 세션 맥락
            profanity_category: Korcen 힌트 (logic: 추가)
            profanity_confidence: 욕설 감지 신뢰도 (logic: 추가)
        
        Returns:
            ClassificationResult (label, label_type, confidence, ...)
        """
        # logic: PipelineMode 기반 분기 처리
        if self.mode != PipelineMode.default() and self.special_label_filter:
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
        
        # HEAD: 기본 로직 유지
        # 욕설 감지 시 즉시 특수 Label 반환
        if profanity_detected:
            # logic: Korcen 힌트 확인
            if profanity_category and profanity_category in self.KORCEN_HINT_MAPPING:
                label = self.KORCEN_HINT_MAPPING[profanity_category]
                return ClassificationResult(
                    label=label,
                    label_type="SPECIAL",
                    confidence=profanity_confidence if profanity_confidence > 0 else 1.0,
                    text=text,
                    timestamp=datetime.now()
                )
            
            # HEAD: 기본 PROFANITY 반환
            return ClassificationResult(
                label="PROFANITY",
                label_type="SPECIAL",
                confidence=1.0,
                text=text,
                timestamp=datetime.now()
            )
        
        # Baseline 규칙으로 특수 Label 사전 감지
        baseline_results = self.baseline_rules.detect_special_labels(text, session_context)
        if baseline_results:
            # 가장 높은 신뢰도의 Label 선택
            if isinstance(baseline_results, list):
                # HEAD 방식: List[Tuple]
                label, confidence = max(baseline_results, key=lambda x: x[1])
            else:
                # logic 방식: ClassificationResult
                label = baseline_results.label
                confidence = baseline_results.confidence
            
            return ClassificationResult(
                label=label,
                label_type="SPECIAL",
                confidence=confidence,
                text=text,
                timestamp=datetime.now()
            )
        
        # KoSentenceBERT로 Normal Label 분류 (향후 구현)
        if self.classifier:
            intent_result = self.classifier.predict(text, session_context)
            label_type = self._determine_label_type(intent_result.label)
            
            return ClassificationResult(
                label=intent_result.label,
                label_type=label_type,
                confidence=intent_result.confidence,
                text=text,
                probabilities=intent_result.probabilities,
                timestamp=datetime.now()
            )
        
        # 모델이 없을 경우 기본값 (임시)
        # 실제 구현 시에는 모델이 필수
        return ClassificationResult(
            label="INQUIRY",  # 기본값
            label_type="NORMAL",
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
    
    def _determine_label_type(self, label: str) -> str:
        """
        Label 타입 결정 (Normal or Special) (HEAD: 유지)
        
        Args:
            label: 분류된 Label
        
        Returns:
            "NORMAL" or "SPECIAL"
        """
        if label in NORMAL_LABELS:
            return "NORMAL"
        elif label in SPECIAL_LABELS:
            return "SPECIAL"
        else:
            return "UNKNOWN"
    
    # logic: PipelineMode 기반 메서드들
    def _predict_fast_classify_then_conditional_detail(
        self,
        text: str,
        profanity_detected: bool,
        session_context: Optional[List[str]],
        profanity_category: Optional[str],
        profanity_confidence: float
    ) -> ClassificationResult:
        """모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL (logic: 추가)"""
        # Korcen 힌트 확인
        if profanity_detected and profanity_category:
            label = self.KORCEN_HINT_MAPPING.get(profanity_category)
            
            if label:
                # 조건 확인: 모델 사용 필요?
                use_model = (
                    profanity_confidence < 0.7 or
                    profanity_category == "PROFANITY_DETECTED"
                )
                
                if use_model and self.special_label_filter:
                    detection = self.special_label_filter.detect(text, session_context)
                    if detection:
                        return ClassificationResult(
                            label=detection.label,
                            label_type=LabelType.SPECIAL.value,
                            confidence=detection.confidence,
                            text=text,
                            timestamp=datetime.now()
                        )
                
                return ClassificationResult(
                    label=label,
                    label_type=LabelType.SPECIAL.value,
                    confidence=profanity_confidence,
                    text=text,
                    timestamp=datetime.now()
                )
        
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
        """모드 2: CLASSIFY_BOTH_ALWAYS (logic: 추가)"""
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
        """모드 3: DETAIL_FIRST_THEN_VERIFY (logic: 추가)"""
        # SpecialLabelFilter.detect() (우선 실행)
        if self.special_label_filter:
            detection = self.special_label_filter.detect(text, session_context)
            if detection:
                confidence = detection.confidence
                
                if profanity_detected and profanity_category:
                    korcen_label = self.KORCEN_HINT_MAPPING.get(profanity_category)
                    
                    if korcen_label == detection.label:
                        confidence = min(1.0, confidence + 0.1)
                    else:
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
        """Normal Label 분류 (기본값: INQUIRY) (logic: 추가)"""
        return ClassificationResult(
            label=NormalLabel.INQUIRY.value,
            label_type=LabelType.NORMAL.value,
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
    
    def _default_result(self, text: str) -> ClassificationResult:
        """기본 결과 (에러 처리) (logic: 추가)"""
        return ClassificationResult(
            label=NormalLabel.INQUIRY.value,
            label_type=LabelType.UNKNOWN.value,
            confidence=0.5,
            text=text,
            timestamp=datetime.now()
        )
