"""
발화 의도 예측 통합 인터페이스

Turn 단위 분석에 맞게 수정
"""

from typing import Optional, List
from datetime import datetime
import warnings

from .baseline_rules import IntentBaselineRules
from .sentence_classifier import SentenceClassifier
from ..data.data_structures import ClassificationResult
from ..config.labels import NORMAL_LABELS, SPECIAL_LABELS


class IntentPredictor:
    """발화 의도 예측기"""
    
    def __init__(self, use_model: bool = True, model_path: Optional[str] = None):
        """
        발화 의도 예측기 초기화
        
        Args:
            use_model: 모델 분류기 사용 여부 (True이면 모델 사용, False이면 baseline 규칙만 사용)
            model_path: 모델 경로 (None이면 기본 경로 사용)
        """
        # 모델 분류기 로드
        if use_model:
            try:
                self.classifier = SentenceClassifier(model_path=model_path)
                if not self.classifier.is_available():
                    warnings.warn("모델 분류기를 사용할 수 없습니다. Baseline 규칙만 사용합니다.")
                    self.classifier = None
                else:
                    print("모델 분류기 로드 완료")
            except Exception as e:
                warnings.warn(f"모델 분류기 로드 실패: {e}. Baseline 규칙만 사용합니다.")
                self.classifier = None
        else:
            self.classifier = None
        
        # Baseline 규칙은 모듈 내부에 포함
        self.baseline_rules = IntentBaselineRules()
    
    def predict(self, text: str, profanity_detected: bool, profanity_confidence: float = 0.0,
                session_context: Optional[List[str]] = None) -> ClassificationResult:
        """
        발화 의도 예측 (통합)
        
        접근 방식:
        - Special Label: korcen + baseline 규칙 요인들을 합산하여 신뢰도 계산
        - Normal Label: Special Label이 아닌 경우 기본값으로 분류 (confidence는 낮게)
        
        주의: Turn 단위 분석이므로 session_context는 최소 사용
        
        Args:
            text: 분석할 문장 (해당 Turn만)
            profanity_detected: 1차 필터링에서 욕설 감지 여부
            profanity_confidence: 욕설 감지 신뢰도 (0.0-1.0)
            session_context: 세션 맥락 (선택사항, 최소 사용)
        
        Returns:
            ClassificationResult (label, label_type, confidence, ...)
        """
        # Special Label 감지 요인 수집 (korcen + baseline 규칙 + 모델)
        special_factors = []  # [(label, confidence), ...]
        
        # 1. 욕설 감지 (korcen/baseline)
        if profanity_detected:
            special_factors.append(("PROFANITY", profanity_confidence))
        
        # 2. Baseline 규칙으로 Special Label 감지 (Turn 단위)
        baseline_results = self.baseline_rules.detect_special_labels(text, session_context)
        special_factors.extend(baseline_results)
        
        # 3. 모델로 Special Label 예측 (모델이 사용 가능한 경우)
        if self.classifier and self.classifier.is_available():
            try:
                model_result = self.classifier.predict(text, return_probabilities=True)
                # 모델이 Special Label로 예측한 경우 추가
                if model_result.get('label_type') == 'SPECIAL':
                    model_label = model_result.get('label')
                    model_confidence = model_result.get('confidence', 0.0)
                    # 기존에 같은 label이 없거나, 모델 신뢰도가 더 높은 경우 추가/업데이트
                    existing_label_idx = None
                    for i, (label, conf) in enumerate(special_factors):
                        if label == model_label:
                            existing_label_idx = i
                            break
                    
                    if existing_label_idx is not None:
                        # 기존 신뢰도와 모델 신뢰도 중 높은 값 사용
                        _, existing_conf = special_factors[existing_label_idx]
                        special_factors[existing_label_idx] = (model_label, max(existing_conf, model_confidence))
                    else:
                        # 새로운 Special Label 추가
                        special_factors.append((model_label, model_confidence))
            except Exception as e:
                # 모델 예측 실패 시 무시하고 계속 진행
                warnings.warn(f"모델 예측 중 오류 발생: {e}")
        
        # Special Label 요인들이 있는 경우
        if special_factors:
            # 가장 높은 신뢰도의 Label 선택
            primary_label, primary_confidence = max(special_factors, key=lambda x: x[1])
            
            # 모든 요인들을 합산하여 special_label_confidence 계산
            # 각 요인의 신뢰도를 가중 합산 (최대값 기준 정규화)
            total_confidence = sum(conf for _, conf in special_factors)
            # 요인 개수에 따라 가중치 조정 (요인이 많을수록 신뢰도 상승)
            factor_count = len(special_factors)
            special_label_confidence = min(
                max(primary_confidence, total_confidence / factor_count) * (1.0 + (factor_count - 1) * 0.1),
                1.0
            )
            
            # 모든 Special Label 요인을 probabilities에 저장
            probabilities = {}
            total_factor_confidence = sum(conf for _, conf in special_factors)
            if total_factor_confidence > 0:
                for label, conf in special_factors:
                    probabilities[label] = conf / total_factor_confidence
            
            return ClassificationResult(
                label=primary_label,
                label_type="SPECIAL",
                confidence=special_label_confidence,
                text=text,
                probabilities=probabilities,
                timestamp=datetime.now()
            )
        
        # Special Label이 아닌 경우: Normal Label로 분류
        # 1. 모델로 Normal Label 예측 시도 (모델이 사용 가능한 경우)
        if self.classifier and self.classifier.is_available():
            try:
                model_result = self.classifier.predict(text, return_probabilities=True)
                # 모델이 Normal Label로 예측한 경우
                if model_result.get('label_type') == 'NORMAL':
                    label = model_result.get('label')
                    confidence = model_result.get('confidence', 0.3)
                    probabilities = model_result.get('probabilities', {label: 1.0})
                    
                    return ClassificationResult(
                        label=label,
                        label_type="NORMAL",
                        confidence=confidence,
                        text=text,
                        probabilities=probabilities,
                        timestamp=datetime.now()
                    )
            except Exception as e:
                # 모델 예측 실패 시 baseline 규칙 사용
                warnings.warn(f"모델 예측 중 오류 발생: {e}. Baseline 규칙 사용")
        
        # 2. Baseline 규칙으로 Normal Label 분류
        normal_baseline_results = self.baseline_rules.detect_normal_labels(text, session_context)
        
        if normal_baseline_results:
            # 가장 높은 신뢰도의 Normal Label 선택
            label, _ = max(normal_baseline_results, key=lambda x: x[1])
        else:
            # 기본값: INQUIRY
            label = "INQUIRY"
        
        # Normal Label은 confidence를 낮게 설정 (정량화하기 어려움)
        # Special Label이 아니라는 것만으로는 정상 발화의 근거를 확신할 수 없음
        return ClassificationResult(
            label=label,
            label_type="NORMAL",
            confidence=0.3,  # 낮은 신뢰도 (Special Label이 아닐 뿐)
            text=text,
            probabilities={label: 1.0},
            timestamp=datetime.now()
        )
    
    def _determine_label_type(self, label: str) -> str:
        """
        Label 타입 결정 (Normal or Special)
        
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


