"""
파이프라인 모듈

재설계: 세 단계 세션 구조
- BaselineValidationSession: baseline keyword 검증 + AI hub 모델 검증
- IntensityValidationSession: special label만 intensity 검증
- FinalScoreCalculationSession: 최종 점수 계산

자세한 내용은 PIPELINE_REDESIGN_DOCUMENTATION.md 참조
"""

from .main_pipeline import MainPipeline
from .baseline_validation_session import BaselineValidationSession
from .intensity_validation_session import IntensityValidationSession
from .final_score_calculation_session import FinalScoreCalculationSession
from .session_utils import (
    validate_score,
    validate_text,
    validate_label,
    validate_label_type
)

__all__ = [
    'MainPipeline',
    'BaselineValidationSession',
    'IntensityValidationSession',
    'FinalScoreCalculationSession',
    'validate_score',
    'validate_text',
    'validate_label',
    'validate_label_type'
]
