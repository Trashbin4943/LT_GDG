"""
Models 모듈

학습된 모델 파일들을 관리하는 모듈
"""

from pathlib import Path

# Models 디렉토리 경로
MODELS_DIR = Path(__file__).parent
AIHUB_MODEL_DIR = MODELS_DIR / 'aihub' / 'base_model'

