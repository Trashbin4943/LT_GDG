"""
Intensity Validation Session (두 번째 세션)

후반부 처리:
- Special label로 분류된 것들만 intensity 검증
- Float 기반 intensity 검증 (0.0 ~ 3.0)
- 단계 기반 intensity 검증 (LOW, MEDIUM, HIGH, VERY_HIGH)

의존성:
- IntensityRegressionModel: Float 기반 intensity 모델 (선택적)
- TernaryClassificationModel: 단계 기반 intensity 모델 (선택적)
- ClassificationResult: 결과 데이터 구조 (필수)
- LabelType: 라벨 타입 정의 (필수)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models.intensity_regression_model import IntensityRegressionModel
from ..models.ternary_classification_model import TernaryClassificationModel
from ..data.data_structures import ClassificationResult
from ..config.labels import LabelType

logger = logging.getLogger(__name__)


class IntensityValidationSession:
    """
    Intensity Validation Session
    
    후반부 처리 세션:
    - Special label로 분류된 것들만 intensity 검증
    - Float 기반 intensity 검증 (0.0 ~ 3.0)
    - 단계 기반 intensity 검증 (LOW, MEDIUM, HIGH, VERY_HIGH)
    """
    
    def __init__(
        self,
        intensity_model: Optional[IntensityRegressionModel] = None,
        ternary_model: Optional[TernaryClassificationModel] = None,
        intensity_model_path: Optional[str] = None,
        ternary_model_path: Optional[str] = None
    ):
        """
        Intensity Validation Session 초기화
        
        모델 초기화 우선순위:
        1. 인스턴스 직접 전달 (intensity_model, ternary_model)
        2. 모델 경로로 로드 (intensity_model_path, ternary_model_path)
        3. None (모델 없이 사용, 검증 스킵)
        
        Args:
            intensity_model: Intensity Regression 모델 인스턴스 (선택적, 우선순위 1)
            ternary_model: Ternary Classification 모델 인스턴스 (선택적, 우선순위 1)
            intensity_model_path: Intensity Regression 모델 경로 (우선순위 2)
            ternary_model_path: Ternary Classification 모델 경로 (우선순위 2)
        
        Raises:
            None (에러 발생 시 경고 로그만 출력하고 계속 진행)
        """
        # Intensity Regression 모델 초기화 (우선순위: intensity_model > intensity_model_path > None)
        if intensity_model:
            self.intensity_model = intensity_model
            logger.debug("Intensity Regression 모델 인스턴스를 직접 사용합니다.")
        elif intensity_model_path:
            try:
                self.intensity_model = IntensityRegressionModel(intensity_model_path)
                logger.debug(f"Intensity Regression 모델 로드 완료: {intensity_model_path}")
            except Exception as e:
                logger.warning(f"Intensity Regression 모델 초기화 실패: {e}. Float 기반 검증을 스킵합니다.")
                self.intensity_model = None
        else:
            self.intensity_model = None
            logger.debug("Intensity Regression 모델을 사용하지 않습니다.")
        
        # Ternary Classification 모델 초기화 (우선순위: ternary_model > ternary_model_path > None)
        if ternary_model:
            self.ternary_model = ternary_model
            logger.debug("Ternary Classification 모델 인스턴스를 직접 사용합니다.")
        elif ternary_model_path:
            try:
                self.ternary_model = TernaryClassificationModel(ternary_model_path)
                logger.debug(f"Ternary Classification 모델 로드 완료: {ternary_model_path}")
            except Exception as e:
                logger.warning(f"Ternary Classification 모델 초기화 실패: {e}. 단계 기반 검증을 스킵합니다.")
                self.ternary_model = None
        else:
            self.ternary_model = None
            logger.debug("Ternary Classification 모델을 사용하지 않습니다.")
    
    def validate(
        self,
        classification_result: ClassificationResult
    ) -> ClassificationResult:
        """
        Special label에 대한 intensity 검증 수행
        
        처리 순서:
        1. Special label 여부 확인 (아니면 그대로 반환)
        2. Float 기반 intensity 검증 (모델이 있는 경우)
        3. 단계 기반 intensity 검증 (모델이 있는 경우)
        4. 두 결과의 일치성 검증
        
        Args:
            classification_result: 첫 번째 세션(BaselineValidationSession)에서 분류된 결과
                - label_type이 "SPECIAL"인 경우만 검증 수행
                - "NORMAL"인 경우 그대로 반환
        
        Returns:
            ClassificationResult: intensity 정보가 추가된 결과
                - intensity: Float 값 (0.0 ~ 3.0, 모델이 있는 경우)
                - intensity_level: 단계 값 (LOW, MEDIUM, HIGH, VERY_HIGH, 모델이 있는 경우)
                - is_immoral: 비윤리 여부 (모델이 있는 경우)
                - immorality_confidence: 비윤리 신뢰도 (모델이 있는 경우)
                - metadata: intensity_level_confidence, intensity_level_probabilities, intensity_mismatch (있는 경우)
        
        Note:
            - Special label이 아닌 경우 검증을 스킵하고 원본 결과를 그대로 반환
            - 모델이 없는 경우 intensity 정보 없이 원본 결과 반환
            - 두 모델의 결과가 불일치하는 경우 metadata에 기록
        """
        # Special label이 아닌 경우 그대로 반환
        if classification_result.label_type != LabelType.SPECIAL.value:
            logger.debug(f"Special label이 아니므로 intensity 검증 스킵: {classification_result.label}")
            return classification_result
        
        text = classification_result.text
        
        # ==========================================
        # 1단계: Float 기반 intensity 검증
        # ==========================================
        intensity_result = None
        if self.intensity_model and self.intensity_model.is_available():
            try:
                intensity_result = self.intensity_model.predict(text)
                
                # ClassificationResult에 intensity 정보 추가
                classification_result.intensity = intensity_result['intensity']
                classification_result.is_immoral = intensity_result['is_immoral']
                classification_result.immorality_confidence = intensity_result['immorality_confidence']
                
                logger.debug(
                    f"Intensity 검증 완료: intensity={intensity_result['intensity']:.2f}, "
                    f"is_immoral={intensity_result['is_immoral']}"
                )
            except Exception as e:
                logger.warning(f"Intensity Regression 모델 예측 실패: {e}")
        
        # ==========================================
        # 2단계: 단계 기반 intensity 검증
        # ==========================================
        ternary_result = None
        if self.ternary_model and self.ternary_model.is_available():
            try:
                ternary_result = self.ternary_model.predict(text)
                
                # ClassificationResult에 intensity_level 정보 추가
                classification_result.intensity_level = ternary_result['intensity_level']
                
                # 메타데이터에 확률 정보 추가
                if not hasattr(classification_result, 'metadata') or classification_result.metadata is None:
                    classification_result.metadata = {}
                classification_result.metadata['intensity_level_confidence'] = ternary_result['intensity_level_confidence']
                classification_result.metadata['intensity_level_probabilities'] = ternary_result['probabilities']
                
                logger.debug(
                    f"Intensity 단계 검증 완료: level={ternary_result['intensity_level']}, "
                    f"confidence={ternary_result['intensity_level_confidence']:.2f}"
                )
            except Exception as e:
                logger.warning(f"Ternary Classification 모델 예측 실패: {e}")
        
        # ==========================================
        # Intensity 정보 통합 검증
        # ==========================================
        # Float 기반과 단계 기반 결과가 일치하는지 확인
        if intensity_result and ternary_result:
            intensity = intensity_result['intensity']
            level = ternary_result['intensity_level']
            
            # 일치성 검증
            expected_level = self._get_expected_level_from_intensity(intensity)
            if expected_level != level:
                logger.warning(
                    f"Intensity 불일치: float={intensity:.2f} (예상 level={expected_level}), "
                    f"실제 level={level}"
                )
                # 메타데이터에 불일치 정보 추가
                if classification_result.metadata is None:
                    classification_result.metadata = {}
                classification_result.metadata['intensity_mismatch'] = {
                    'float_intensity': intensity,
                    'expected_level': expected_level,
                    'actual_level': level
                }
        
        return classification_result
    
    def _get_expected_level_from_intensity(self, intensity: float) -> str:
        """
        Float intensity 값으로부터 예상되는 단계 반환
        
        Args:
            intensity: Float intensity 값 (0.0 ~ 3.0)
        
        Returns:
            예상 단계 (LOW, MEDIUM, HIGH, VERY_HIGH)
        """
        if intensity == 0.0:
            return 'LOW'
        elif intensity < 1.0:
            return 'LOW'
        elif intensity < 2.0:
            return 'MEDIUM'
        elif intensity < 3.0:
            return 'HIGH'
        else:
            return 'VERY_HIGH'
    
    def validate_batch(
        self,
        classification_results: List[ClassificationResult]
    ) -> List[ClassificationResult]:
        """
        여러 ClassificationResult에 대해 일괄 intensity 검증
        
        Args:
            classification_results: ClassificationResult 리스트
        
        Returns:
            intensity 정보가 추가된 ClassificationResult 리스트
        """
        validated_results = []
        
        for result in classification_results:
            # Special label만 검증
            if result.label_type == LabelType.SPECIAL.value:
                validated_result = self.validate(result)
                validated_results.append(validated_result)
            else:
                # Special label이 아닌 경우 그대로 추가
                validated_results.append(result)
        
        return validated_results
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        세션 정보 반환 (디버깅 및 모니터링용)
        
        Returns:
            Dict: 세션 상태 정보
        """
        return {
            'has_intensity_model': self.intensity_model is not None and (
                self.intensity_model.is_available() if hasattr(self.intensity_model, 'is_available') else True
            ),
            'has_ternary_model': self.ternary_model is not None and (
                self.ternary_model.is_available() if hasattr(self.ternary_model, 'is_available') else True
            ),
            'session_type': 'IntensityValidationSession'
        }
    
    def is_available(self) -> bool:
        """
        세션이 사용 가능한지 확인 (최소 하나의 모델이 있어야 함)
        
        Returns:
            bool: 사용 가능 여부
        """
        has_intensity = self.intensity_model is not None and (
            self.intensity_model.is_available() if hasattr(self.intensity_model, 'is_available') else True
        )
        has_ternary = self.ternary_model is not None and (
            self.ternary_model.is_available() if hasattr(self.ternary_model, 'is_available') else True
        )
        return has_intensity or has_ternary

