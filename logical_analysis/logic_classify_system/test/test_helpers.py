"""
테스트 헬퍼 함수
모든 테스트에서 공통으로 사용하는 유틸리티 함수
"""

from pathlib import Path
from typing import Optional
from logical_analysis.logic_classify_system.pipeline.main_pipeline import MainPipeline
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)


def create_test_pipeline(use_models: bool = True) -> MainPipeline:
    """
    테스트용 MainPipeline 생성
    
    Args:
        use_models: 모델 사용 여부 (기본: True)
                    False인 경우 Baseline 규칙만 사용
    
    Returns:
        MainPipeline 인스턴스
    """
    if use_models:
        # 새로운 모델 경로 시스템 사용
        intensity_model_path = get_intensity_model_path()
        ternary_model_path = get_ternary_model_path()
        
        return MainPipeline(
            intensity_model_path=intensity_model_path,
            ternary_model_path=ternary_model_path,
            use_enhanced_predictor=True
        )
    else:
        # Baseline 규칙만 사용
        return MainPipeline(
            intensity_model_path=None,
            ternary_model_path=None,
            use_enhanced_predictor=False
        )

