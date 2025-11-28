"""
Intensity Regression 모델 (checkpoint-68000)
비윤리 강도를 연속값으로 예측
"""

import torch
from pathlib import Path
from typing import Dict, Optional
import warnings

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("transformers 라이브러리가 설치되지 않았습니다. Intensity 모델을 사용할 수 없습니다.")


class IntensityRegressionModel:
    """Intensity Regression 모델"""
    
    def __init__(self, model_path: str, use_gpu: bool = True):
        """
        Intensity Regression 모델 초기화
        
        Args:
            model_path: 체크포인트 경로 (예: "models/checkpoints/intensity_regression/intensity_model")
            use_gpu: GPU 사용 여부
        """
        if not TRANSFORMERS_AVAILABLE:
            self.model = None
            self.tokenizer = None
            self.device = None
            warnings.warn("transformers 라이브러리가 없어 Intensity 모델을 로드할 수 없습니다.")
            return
        
        self.model_path = Path(model_path)
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """모델 및 토크나이저 로드"""
        if not TRANSFORMERS_AVAILABLE:
            return
        
        if not self.model_path.exists():
            warnings.warn(f"Intensity 모델 경로가 존재하지 않습니다: {self.model_path}")
            self.model = None
            self.tokenizer = None
            return
        
        try:
            # 커스텀 토크나이저를 사용하므로 trust_remote_code=True 필요
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path),
                trust_remote_code=True
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path),
                trust_remote_code=True
            )
            self.model.to(self.device)
            self.model.eval()
            print(f"✅ Intensity Regression 모델 로드 완료: {self.model_path} (장치: {self.device})")
        except Exception as e:
            warnings.warn(f"Intensity Regression 모델 로드 실패: {e}")
            self.model = None
            self.tokenizer = None
    
    def predict(self, text: str, max_length: int = 128) -> Dict[str, any]:
        """
        Intensity 예측
        
        Args:
            text: 분석할 텍스트
            max_length: 최대 토큰 길이
        
        Returns:
            {
                'intensity': float,  # 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
                'is_immoral': bool,  # intensity > 0.0
                'immorality_confidence': float  # intensity 기반 신뢰도
            }
        """
        if self.model is None or self.tokenizer is None:
            return {
                'intensity': 0.0,
                'is_immoral': False,
                'immorality_confidence': 0.0
            }
        
        try:
            # 토크나이징
            encoding = self.tokenizer(
                text,
                truncation=True,
                padding='max_length',
                max_length=max_length,
                return_tensors='pt'
            )
            
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            # 예측
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                # Regression 모델: logits가 하나의 실수 값
                intensity = max(0.0, outputs.logits.item())  # 음수 방지
            
            # is_immoral 판단
            is_immoral = intensity > 0.0
            
            # immorality_confidence 계산
            # intensity가 높을수록 신뢰도 상승 (0.0-1.0 범위로 정규화)
            # intensity 범위: 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
            immorality_confidence = min(intensity / 3.0, 1.0) if is_immoral else 0.0
            
            return {
                'intensity': float(intensity),
                'is_immoral': is_immoral,
                'immorality_confidence': float(immorality_confidence)
            }
        except Exception as e:
            warnings.warn(f"Intensity 예측 실패: {e}")
            return {
                'intensity': 0.0,
                'is_immoral': False,
                'immorality_confidence': 0.0
            }
    
    def is_available(self) -> bool:
        """모델 사용 가능 여부"""
        return self.model is not None and self.tokenizer is not None

