"""
모델 설정 관리
"""
import os
from typing import Dict, Optional
from pathlib import Path


class ModelConfig:
    """모델 경로 및 설정 관리"""
    
    DEFAULT_BASE_MODEL_PATH = "./model"
    DEFAULT_MODEL1_CHECKPOINT = "./ckpt/class/checkpoint-56000"
    DEFAULT_MODEL2_CHECKPOINT = "./ckpt/multi/checkpoint-XXXX"
    
    @staticmethod
    def check_model_availability(use_external: bool = False) -> Dict[str, bool]:
        """
        모델 파일 가용성 확인
        
        Args:
            use_external: 외부 경로 사용 여부
        
        Returns:
            모델 파일 존재 여부 딕셔너리
        """
        result = {
            "base_model": False,
            "model1_checkpoint": False,
            "model2_checkpoint": False,
            "tokenizer": False
        }
        
        base_path = ModelConfig.DEFAULT_BASE_MODEL_PATH
        if os.path.exists(base_path):
            result["base_model"] = True
            # 토크나이저 확인
            tokenizer_path = os.path.join(base_path, "tokenizer")
            if os.path.exists(tokenizer_path) or os.path.exists(os.path.join(base_path, "vocab.txt")):
                result["tokenizer"] = True
        
        if os.path.exists(ModelConfig.DEFAULT_MODEL1_CHECKPOINT):
            result["model1_checkpoint"] = True
        
        if os.path.exists(ModelConfig.DEFAULT_MODEL2_CHECKPOINT):
            result["model2_checkpoint"] = True
        
        return result
    
    @staticmethod
    def get_model_paths(
        base_model_path: Optional[str] = None,
        model1_checkpoint: Optional[str] = None,
        model2_checkpoint: Optional[str] = None
    ) -> Dict[str, str]:
        """
        모델 경로 반환 (기본값 또는 사용자 지정 경로)
        
        Args:
            base_model_path: 기본 모델 경로
            model1_checkpoint: 모델 1 체크포인트 경로
            model2_checkpoint: 모델 2 체크포인트 경로
        
        Returns:
            모델 경로 딕셔너리
        """
        return {
            "base_model_path": base_model_path or ModelConfig.DEFAULT_BASE_MODEL_PATH,
            "model1_checkpoint": model1_checkpoint or ModelConfig.DEFAULT_MODEL1_CHECKPOINT,
            "model2_checkpoint": model2_checkpoint or ModelConfig.DEFAULT_MODEL2_CHECKPOINT
        }
