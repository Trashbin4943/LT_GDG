"""
모델 경로 설정
환경 변수 및 프로젝트 내부 경로를 지원하는 유연한 모델 경로 관리
"""

import os
from pathlib import Path
from typing import Optional


# 프로젝트 루트 기준 모델 디렉토리
# model_paths.py 위치: logical_analysis/logic_classify_system/config/model_paths.py
# parent 1: logical_analysis/logic_classify_system/config
# parent 2: logical_analysis/logic_classify_system
# parent 3: logical_analysis (이것이 _PROJECT_ROOT)
# 따라서 _PROJECT_ROOT는 logical_analysis 디렉토리
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MODELS_BASE_DIR = _PROJECT_ROOT / "logic_classify_system" / "models" / "checkpoints"

# 모델 디렉토리 구조
INTENSITY_MODEL_DIR = _MODELS_BASE_DIR / "intensity_regression" / "intensity_model"
TERNARY_MODEL_DIR = _MODELS_BASE_DIR / "ternary_classification" / "ternary_model"


def _get_path_from_env(env_var: str) -> Optional[Path]:
    """
    환경 변수에서 경로 가져오기
    
    Args:
        env_var: 환경 변수 이름
    
    Returns:
        경로 (존재하는 경우) 또는 None
    """
    path_str = os.getenv(env_var)
    if path_str:
        path = Path(path_str)
        if path.exists():
            return path
    return None


def _get_path_from_default(default_path: Path) -> Optional[Path]:
    """
    기본 경로에서 모델 경로 가져오기
    
    Args:
        default_path: 기본 경로
    
    Returns:
        경로 (존재하는 경우) 또는 None
    """
    if default_path.exists():
        return default_path
    return None


def get_intensity_model_path() -> Optional[str]:
    """
    Intensity Regression 모델 경로 반환
    
    우선순위:
    1. 환경 변수 (INTENSITY_MODEL_PATH)
    2. 프로젝트 내부 경로 (models/checkpoints/intensity_regression/intensity_model)
    
    Returns:
        모델 경로 (존재하는 경우) 또는 None
    """
    # 1. 환경 변수 확인
    env_path = _get_path_from_env("INTENSITY_MODEL_PATH")
    if env_path:
        return str(env_path)
    
    # 2. 프로젝트 내부 경로 확인
    project_path = _get_path_from_default(INTENSITY_MODEL_DIR)
    if project_path:
        return str(project_path)
    
    # 모델 경로를 찾을 수 없음
    return None


def get_ternary_model_path() -> Optional[str]:
    """
    3진 분류 모델 경로 반환
    
    우선순위:
    1. 환경 변수 (TERNARY_MODEL_PATH)
    2. 프로젝트 내부 경로 (models/checkpoints/ternary_classification/ternary_model)
    
    Returns:
        모델 경로 (존재하는 경우) 또는 None
    """
    # 1. 환경 변수 확인
    env_path = _get_path_from_env("TERNARY_MODEL_PATH")
    if env_path:
        return str(env_path)
    
    # 2. 프로젝트 내부 경로 확인
    project_path = _get_path_from_default(TERNARY_MODEL_DIR)
    if project_path:
        return str(project_path)
    
    # 모델 경로를 찾을 수 없음
    return None


def get_model_base_dir() -> Path:
    """
    모델 기본 디렉토리 경로 반환
    
    Returns:
        모델 기본 디렉토리 Path
    """
    return _MODELS_BASE_DIR


def ensure_model_directories():
    """
    모델 디렉토리 생성 (존재하지 않는 경우)
    """
    INTENSITY_MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    TERNARY_MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
