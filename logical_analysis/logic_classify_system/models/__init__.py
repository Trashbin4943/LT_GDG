"""
Models 모듈

학습된 모델 파일들을 관리하는 모듈
"""

from pathlib import Path

# Models 디렉토리 경로
MODELS_DIR = Path(__file__).parent
AIHUB_MODEL_DIR = MODELS_DIR / 'aihub' / 'base_model'

# 이중 모델 통합 모델 클래스
from .intensity_regression_model import IntensityRegressionModel
from .ternary_classification_model import TernaryClassificationModel

__all__ = [
    'IntensityRegressionModel',
    'TernaryClassificationModel',
    'MODELS_DIR',
    'AIHUB_MODEL_DIR'
]

