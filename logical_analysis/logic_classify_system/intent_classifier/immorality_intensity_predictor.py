"""
비윤리 강도 예측 모듈

학습된 KoBERT Regression 모델을 사용하여 발화의 비윤리 강도를 예측합니다.
"""

import torch
from pathlib import Path
from typing import Optional, Dict
import warnings

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("transformers 라이브러리가 설치되지 않았습니다.")


class ImmoralityIntensityPredictor:
    """비윤리 강도 예측기"""
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True):
        """
        비윤리 강도 예측기 초기화
        
        Args:
            model_path: 모델 경로 (None이면 기본 경로 사용)
            use_gpu: GPU 사용 여부
        """
        if not TRANSFORMERS_AVAILABLE:
            self.model = None
            self.tokenizer = None
            self.device = None
            warnings.warn("transformers 라이브러리가 없어 모델을 로드할 수 없습니다.")
            return
        
        # 모델 경로 설정
        if model_path is None:
            current_dir = Path(__file__).parent.parent
            model_path = str(current_dir / 'models' / 'immorality_intensity')
        
        self.model_path = Path(model_path)
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        
        # 모델 로드
        self._load_model()
    
    def _load_model(self):
        """모델 및 토크나이저 로드"""
        if not TRANSFORMERS_AVAILABLE:
            return
        
        if not self.model_path.exists():
            warnings.warn(f"모델 경로가 존재하지 않습니다: {self.model_path}")
            self.model = None
            self.tokenizer = None
            return
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path)
            )
            self.model = self.model.to(self.device)
            self.model.eval()
            print(f"비윤리 강도 모델 로드 완료: {self.model_path} (장치: {self.device})")
        except Exception as e:
            warnings.warn(f"모델 로드 중 오류 발생: {e}")
            self.model = None
            self.tokenizer = None
    
    def predict(self, text: str, max_length: int = 128) -> Dict[str, float]:
        """
        비윤리 강도 예측
        
        Args:
            text: 예측할 텍스트
            max_length: 최대 토큰 길이
        
        Returns:
            {
                'intensity': float,      # 예측된 비윤리 강도 (0.0 ~ 3.0)
                'is_immoral': bool       # 비윤리 여부 (intensity > 0)
            }
        """
        if self.model is None or self.tokenizer is None:
            return {
                'intensity': 0.0,
                'is_immoral': False
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
            
            # GPU로 이동
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            # 예측
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                predicted_intensity = max(0.0, min(3.0, outputs.logits.item()))  # 0.0 ~ 3.0 범위로 제한
            
            return {
                'intensity': predicted_intensity,
                'is_immoral': predicted_intensity > 0.0
            }
        except Exception as e:
            warnings.warn(f"예측 중 오류 발생: {e}")
            return {
                'intensity': 0.0,
                'is_immoral': False
            }
    
    def is_available(self) -> bool:
        """모델 사용 가능 여부"""
        return self.model is not None and self.tokenizer is not None

