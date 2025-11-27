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
                    if intensity >= 2.5:
                        # 매우 높은 intensity → 강한 Special Label
                        special_factors.append(("INTENSITY_HIGH", immorality_conf))
                    elif intensity >= 1.8:
                        # 높은 intensity → 중간 Special Label
                        special_factors.append(("INTENSITY_MEDIUM", immorality_conf * 0.8))
                    elif intensity > 0.0:
                        # 낮은 intensity → 약한 Special Label
                        special_factors.append(("INTENSITY_LOW", immorality_conf * 0.6))
                    # intensity == 0.0인 경우는 Normal Label로 처리
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
                
                # HIGH 또는 VERY_HIGH 단계인 경우 Special Label 가능성 추가
                if ternary_result['intensity_level'] == 'VERY_HIGH':
                    special_factors.append(
                        ("TERNARY_VERY_HIGH", ternary_result['intensity_level_confidence'])
                    )
                elif ternary_result['intensity_level'] == 'HIGH':
                    special_factors.append(
                        ("TERNARY_HIGH", ternary_result['intensity_level_confidence'] * 0.9)
                    )
                elif ternary_result['intensity_level'] == 'MEDIUM':
                    special_factors.append(
                        ("TERNARY_MEDIUM", ternary_result['intensity_level_confidence'] * 0.7)
                    )
            except Exception as e:
                warnings.warn(f"4진 분류 모델 예측 실패: {e}")
        
        # Special Label 요인들이 있는 경우
        if special_factors:
            # 가장 높은 신뢰도의 Label 선택
            primary_label, primary_confidence = max(special_factors, key=lambda x: x[1])
            
            # 모든 요인들을 합산하여 신뢰도 계산
            total_confidence = sum(conf for _, conf in special_factors)
            factor_count = len(special_factors)
            special_label_confidence = min(
                max(primary_confidence, total_confidence / factor_count) * (1.0 + (factor_count - 1) * 0.1),
                1.0
            )
            
            # probabilities 계산
            probabilities = {}
            total_factor_confidence = sum(conf for _, conf in special_factors)
            if total_factor_confidence > 0:
                for label, conf in special_factors:
                    probabilities[label] = conf / total_factor_confidence
            
            # 실제 Label 결정 (INTENSITY_*, TERNARY_* 제외)
            actual_label = self._determine_actual_label(special_factors, intensity_result, ternary_result)
            
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
        if intensity_result and intensity_result['is_immoral']:
            intensity = intensity_result['intensity']
            # intensity 범위: 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
            if intensity >= 2.5:
                return "VIOLENCE_THREAT"  # 매우 높은 intensity
            elif intensity >= 1.8:
                return "PROFANITY"  # 높은 intensity
            elif intensity > 0.0:
                return "UNREASONABLE_DEMAND"  # 낮은 intensity
        
        # 기본값
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

