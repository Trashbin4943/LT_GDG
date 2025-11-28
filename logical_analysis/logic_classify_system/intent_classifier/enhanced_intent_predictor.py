"""
향상된 의도 예측기 (이중 모델 통합)
Intensity Regression + 3진 분류 모델 통합
"""

from typing import Optional, List
from datetime import datetime
import warnings

from .baseline_rules import IntentBaselineRules
from ..models.intensity_regression_model import IntensityRegressionModel
from ..models.ternary_classification_model import TernaryClassificationModel
from ..data.data_structures import ClassificationResult
from ..config.labels import NORMAL_LABELS, SPECIAL_LABELS


class EnhancedIntentPredictor:
    """향상된 의도 예측기 (이중 모델 통합)"""
    
    def __init__(
        self,
        intensity_model_path: Optional[str] = None,
        ternary_model_path: Optional[str] = None,
        use_models: bool = True
    ):
        """
        향상된 의도 예측기 초기화
        
        Args:
            intensity_model_path: Intensity Regression 모델 경로
            ternary_model_path: 3진 분류 모델 경로
            use_models: 모델 사용 여부
        """
        self.use_models = use_models
        
        # 모델 초기화
        if use_models:
            # Intensity Regression 모델
            if intensity_model_path:
                try:
                    self.intensity_model = IntensityRegressionModel(intensity_model_path)
                except Exception as e:
                    warnings.warn(f"Intensity 모델 로드 실패: {e}")
                    self.intensity_model = None
            else:
                self.intensity_model = None
            
            # 3진 분류 모델
            if ternary_model_path:
                try:
                    self.ternary_model = TernaryClassificationModel(ternary_model_path)
                except Exception as e:
                    warnings.warn(f"3진 분류 모델 로드 실패: {e}")
                    self.ternary_model = None
            else:
                self.ternary_model = None
        else:
            self.intensity_model = None
            self.ternary_model = None
        
        # Baseline 규칙
        self.baseline_rules = IntentBaselineRules()
    
    def predict(
        self,
        text: str,
        profanity_detected: bool = False,
        session_context: Optional[List[str]] = None,
        profanity_category: Optional[str] = None,
        profanity_confidence: float = 0.0
    ) -> ClassificationResult:
        """
        향상된 의도 예측 (이중 모델 통합)
        
        Args:
            text: 분석할 텍스트
            profanity_detected: 욕설 감지 여부
            session_context: 세션 맥락
            profanity_category: 욕설 카테고리 (호환성용, 현재 미사용)
            profanity_confidence: 욕설 신뢰도
        
        Returns:
            ClassificationResult (intensity 정보 포함)
        """
        # ==========================================
        # 모든 손님 발화에 대해 일관적으로 모델 실행
        # Special Label 여부와 관계없이 intensity 정보 수집
        # ==========================================
        
        # Special Label 감지 요인 수집
        special_factors = []
        
        # 1. 욕설 감지 (기존)
        if profanity_detected:
            special_factors.append(("PROFANITY", profanity_confidence))
        
        # 2. Intensity Regression 모델 예측 (모든 발화에 대해 실행)
        # 0.0 ~ 3.0 범위의 float 값 리턴
        intensity_result = None
        if self.intensity_model and self.intensity_model.is_available():
            try:
                intensity_result = self.intensity_model.predict(text)
                
                # intensity 기반 Special Label 판단
                if intensity_result['is_immoral']:
                    intensity = intensity_result['intensity']
                    immorality_conf = intensity_result['immorality_confidence']
                    
                    # intensity가 높을수록 더 강한 Special Label 가능성
                    # intensity 범위: 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
                    # ⚠️ 낮은 intensity(intensity < 1.8)는 실제 라벨이 없으면 NORMAL일 수 있으므로
                    # special_factors에 추가하지 않음 (다른 실제 라벨과 함께 있을 때만 고려)
                    if intensity >= 2.5:
                        # 매우 높은 intensity → 강한 Special Label
                        special_factors.append(("INTENSITY_HIGH", immorality_conf))
                    elif intensity >= 1.8:
                        # 높은 intensity → 중간 Special Label
                        special_factors.append(("INTENSITY_MEDIUM", immorality_conf * 0.8))
                    # intensity < 1.8인 경우는 special_factors에 추가하지 않음
                    # (실제 라벨이 있으면 intensity 정보는 ClassificationResult에만 저장됨)
            except Exception as e:
                warnings.warn(f"Intensity 모델 예측 실패: {e}")
        
        # 3. Baseline 규칙으로 Special Label 감지
        baseline_results = self.baseline_rules.detect_special_labels(text, session_context)
        special_factors.extend(baseline_results)
        
        # 4. 4진 분류 모델 예측 (모든 발화에 대해 실행)
        # 0, 1, 2, 3의 index -> LOW, MEDIUM, HIGH, VERY_HIGH
        ternary_result = None
        if self.ternary_model and self.ternary_model.is_available():
            try:
                ternary_result = self.ternary_model.predict(text)
                
                # HIGH 또는 VERY_HIGH 단계인 경우만 Special Label 가능성 추가
                # ⚠️ MEDIUM은 실제 라벨이 없으면 NORMAL일 수 있으므로 제외
                if ternary_result['intensity_level'] == 'VERY_HIGH':
                    special_factors.append(
                        ("TERNARY_VERY_HIGH", ternary_result['intensity_level_confidence'])
                    )
                elif ternary_result['intensity_level'] == 'HIGH':
                    special_factors.append(
                        ("TERNARY_HIGH", ternary_result['intensity_level_confidence'] * 0.9)
                    )
                # MEDIUM과 LOW는 special_factors에 추가하지 않음
                # (실제 라벨이 있으면 intensity 정보는 ClassificationResult에만 저장됨)
            except Exception as e:
                warnings.warn(f"4진 분류 모델 예측 실패: {e}")
        
        # 실제 라벨(INTENSITY_*, TERNARY_* 제외) 확인
        actual_labels = [
            (label, conf) for label, conf in special_factors
            if not label.startswith("INTENSITY_") and not label.startswith("TERNARY_")
        ]
        
        # 실제 라벨이 있는 경우에만 SPECIAL로 분류
        if actual_labels:
            # 가장 높은 신뢰도의 실제 라벨 선택
            primary_label, primary_confidence = max(actual_labels, key=lambda x: x[1])
            
            # 실제 라벨들의 신뢰도만 사용하여 계산
            actual_total_confidence = sum(conf for _, conf in actual_labels)
            actual_factor_count = len(actual_labels)
            
            # 메타 라벨(INTENSITY_*, TERNARY_*)도 고려하되, 실제 라벨이 우선
            meta_factors = [
                (label, conf) for label, conf in special_factors
                if label.startswith("INTENSITY_") or label.startswith("TERNARY_")
            ]
            
            # 신뢰도 계산: 실제 라벨 신뢰도를 기본으로 하고, 메타 라벨은 보조적으로만 사용
            if meta_factors:
                meta_boost = min(sum(conf for _, conf in meta_factors) / len(meta_factors) * 0.2, 0.2)
                special_label_confidence = min(
                    max(primary_confidence, actual_total_confidence / actual_factor_count) + meta_boost,
                    1.0
                )
            else:
                special_label_confidence = min(
                    max(primary_confidence, actual_total_confidence / actual_factor_count),
                    1.0
                )
            
            # probabilities 계산: 실제 라벨만 포함 (메타 라벨 제외)
            probabilities = {}
            total_actual_confidence = sum(conf for _, conf in actual_labels)
            if total_actual_confidence > 0:
                for label, conf in actual_labels:
                    probabilities[label] = conf / total_actual_confidence
            
            # 실제 Label 결정
            actual_label = primary_label
            
            # ClassificationResult 생성 (intensity 정보 포함)
            classification_result = ClassificationResult(
                label=actual_label,
                label_type="SPECIAL",
                confidence=special_label_confidence,
                text=text,
                probabilities=probabilities,
                timestamp=datetime.now()
            )
            
            # Intensity 정보 추가
            if intensity_result:
                classification_result.intensity = intensity_result['intensity']
                classification_result.is_immoral = intensity_result['is_immoral']
                classification_result.immorality_confidence = intensity_result['immorality_confidence']
            
            if ternary_result:
                classification_result.intensity_level = ternary_result['intensity_level']
            
            return classification_result
        
        # Special Label이 아닌 경우: Normal Label로 분류
        # IntentBaselineRules는 Special Label만 감지하므로, Normal Label은 기본값 사용
        # 향후 Normal Label 분류 로직이 추가되면 여기에 구현
        label = "INQUIRY"  # 기본 Normal Label
        
        # ClassificationResult 생성
        classification_result = ClassificationResult(
            label=label,
            label_type="NORMAL",
            confidence=0.3,
            text=text,
            probabilities={label: 1.0},
            timestamp=datetime.now()
        )
        
        # Intensity 정보 추가 (모든 발화에 대해 일관적으로 수집)
        # Special Label이 아닌 경우에도 intensity 정보는 항상 포함됨
        if intensity_result:
            classification_result.intensity = intensity_result['intensity']
            classification_result.is_immoral = intensity_result['is_immoral']
            classification_result.immorality_confidence = intensity_result['immorality_confidence']
        
        if ternary_result:
            classification_result.intensity_level = ternary_result['intensity_level']
        
        return classification_result
    
    def _determine_actual_label(
        self,
        special_factors: List[tuple],
        intensity_result: Optional[dict],
        ternary_result: Optional[dict]
    ) -> str:
        """
        실제 Special Label 결정
        
        ⚠️ 이 메서드는 더 이상 사용되지 않음 (predict 메서드에서 직접 처리)
        호환성을 위해 유지하되, 실제 로직은 predict 메서드에 있음
        
        Args:
            special_factors: Special Label 요인 리스트
            intensity_result: Intensity 모델 결과
            ternary_result: 3진 분류 모델 결과
        
        Returns:
            실제 Label (PROFANITY, VIOLENCE_THREAT 등)
        """
        # INTENSITY_*, TERNARY_* 제외하고 실제 Label 찾기
        actual_labels = [
            (label, conf) for label, conf in special_factors
            if not label.startswith("INTENSITY_") and not label.startswith("TERNARY_")
        ]
        
        if actual_labels:
            # 실제 Label 중 가장 높은 신뢰도 선택
            return max(actual_labels, key=lambda x: x[1])[0]
        
        # 실제 Label이 없으면 intensity 기반으로 결정
        # ⚠️ 주의: intensity만으로는 정확한 라벨 판단이 어려우므로,
        # 실제 Label이 없는 경우는 NORMAL이어야 하지만, 
        # 이 메서드는 SPECIAL 라벨만 반환하므로 기본값으로 PROFANITY 반환
        # (실제로는 predict 메서드에서 실제 라벨이 없으면 NORMAL로 분류됨)
        if intensity_result and intensity_result['is_immoral']:
            intensity = intensity_result['intensity']
            # intensity 범위: 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
            if intensity >= 2.5:
                return "VIOLENCE_THREAT"  # 매우 높은 intensity
            elif intensity >= 1.8:
                return "PROFANITY"  # 높은 intensity
        
        # 기본값: 실제 Label이 없으면 PROFANITY 반환
        # (하지만 predict 메서드에서는 실제 라벨이 없으면 NORMAL로 분류됨)
        return "PROFANITY"
    
    def get_intensity_info(self, text: str) -> dict:
        """
        Intensity 정보 조회 (별도 호출용)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            {
                'intensity': float,  # 0.0 ~ 2.0
                'intensity_level': str,  # "LOW", "MEDIUM", "HIGH"
                'is_immoral': bool,
                'immorality_confidence': float
            }
        """
        intensity_result = None
        ternary_result = None
        
        if self.intensity_model and self.intensity_model.is_available():
            intensity_result = self.intensity_model.predict(text)
        
        if self.ternary_model and self.ternary_model.is_available():
            ternary_result = self.ternary_model.predict(text)
        
        return {
            'intensity': intensity_result['intensity'] if intensity_result else 0.0,
            'intensity_level': ternary_result['intensity_level'] if ternary_result else 'LOW',
            'is_immoral': intensity_result['is_immoral'] if intensity_result else False,
            'immorality_confidence': intensity_result['immorality_confidence'] if intensity_result else 0.0
        }

