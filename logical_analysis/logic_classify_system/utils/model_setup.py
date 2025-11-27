"""
모델 설정 유틸리티

필수 패키지 확인 및 모델 설정
"""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ModelSetup:
    """모델 설정 유틸리티"""
    
    REQUIRED_PACKAGES = {
        "torch": "PyTorch",
        "transformers": "Transformers",
        "korcen": "Korcen"
    }
    
    OPTIONAL_PACKAGES = {
        "numpy": "NumPy",
        "scipy": "SciPy",
        "sklearn": "scikit-learn"
    }
    
    @staticmethod
    def check_requirements() -> Dict[str, bool]:
        """
        필수 패키지 확인
        
        Returns:
            패키지 설치 여부 딕셔너리
        """
        results = {}
        
        # 필수 패키지 확인
        for package, name in ModelSetup.REQUIRED_PACKAGES.items():
            try:
                __import__(package)
                results[package] = True
                logger.info(f"{name} 설치됨")
            except ImportError:
                results[package] = False
                logger.warning(f"{name} 설치되지 않음")
        
        # 선택 패키지 확인
        for package, name in ModelSetup.OPTIONAL_PACKAGES.items():
            try:
                __import__(package)
                results[package] = True
            except ImportError:
                results[package] = False
                logger.debug(f"{name} 설치되지 않음 (선택사항)")
        
        return results
    
    @staticmethod
    def setup_models(
        base_model_path: Optional[str] = None,
        model1_checkpoint: Optional[str] = None,
        model2_checkpoint: Optional[str] = None,
        copy_models: bool = False
    ) -> Dict[str, bool]:
        """
        모델 설정 (경로 확인 등)
        
        Args:
            base_model_path: 기본 모델 경로
            model1_checkpoint: 모델 1 체크포인트 경로
            model2_checkpoint: 모델 2 체크포인트 경로
            copy_models: 모델 파일 복사 여부
        
        Returns:
            모델 설정 결과 딕셔너리
        """
        import os
        from logic_classify_system.config.model_config import ModelConfig
        
        results = {
            "requirements_met": False,
            "base_model_exists": False,
            "model1_checkpoint_exists": False,
            "model2_checkpoint_exists": False
        }
        
        # 필수 패키지 확인
        requirements = ModelSetup.check_requirements()
        required_met = all(requirements.get(pkg, False) for pkg in ModelSetup.REQUIRED_PACKAGES.keys())
        results["requirements_met"] = required_met
        
        if not required_met:
            logger.warning("필수 패키지가 설치되지 않았습니다.")
            return results
        
        # 모델 경로 확인
        model_paths = ModelConfig.get_model_paths(
            base_model_path=base_model_path,
            model1_checkpoint=model1_checkpoint,
            model2_checkpoint=model2_checkpoint
        )
        
        results["base_model_exists"] = os.path.exists(model_paths["base_model_path"])
        results["model1_checkpoint_exists"] = os.path.exists(model_paths["model1_checkpoint"])
        results["model2_checkpoint_exists"] = os.path.exists(model_paths["model2_checkpoint"])
        
        return results
