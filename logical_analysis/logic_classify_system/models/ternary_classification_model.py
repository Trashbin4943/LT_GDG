"""
3진 분류 모델 (checkpoint-80000)
Intensity를 세 단계로 분류 (LOW, MEDIUM, HIGH)
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
    warnings.warn("transformers 라이브러리가 설치되지 않았습니다. 3진 분류 모델을 사용할 수 없습니다.")


class TernaryClassificationModel:
    """3진 분류 모델"""
    
    # Label ID 매핑
    LABEL_MAPPING = {
        0: 'LOW',
        1: 'MEDIUM',
        2: 'HIGH'
    }
    
    # Intensity 구간 정의 (윤리검증 데이터셋 기반)
    # 주의: 3진 분류는 intensity > 0인 경우만 적용
    # intensity = 0인 경우는 별도로 Normal Label로 처리
    INTENSITY_RANGES = {
        'LOW': (1.0, 1.6),      # 낮은 비윤리 강도
        'MEDIUM': (1.8, 2.4),   # 중간 비윤리 강도
        'HIGH': (2.6, 3.0)      # 높은 비윤리 강도
    }
    
    def __init__(self, model_path: str, use_gpu: bool = True):
        """
        3진 분류 모델 초기화
        
        Args:
            model_path: 체크포인트 경로 (예: "models/checkpoints/ternary_classification/ternary_model")
            use_gpu: GPU 사용 여부
        """
        if not TRANSFORMERS_AVAILABLE:
            self.model = None
            self.tokenizer = None
            self.device = None
            warnings.warn("transformers 라이브러리가 없어 3진 분류 모델을 로드할 수 없습니다.")
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
            warnings.warn(f"3진 분류 모델 경로가 존재하지 않습니다: {self.model_path}")
            self.model = None
            self.tokenizer = None
            return
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path)
            )
            self.model.to(self.device)
            self.model.eval()
            print(f"✅ 3진 분류 모델 로드 완료: {self.model_path} (장치: {self.device})")
        except Exception as e:
            warnings.warn(f"3진 분류 모델 로드 실패: {e}")
            self.model = None
            self.tokenizer = None
    
    def predict(self, text: str, max_length: int = 128) -> Dict[str, any]:
        """
        3진 분류 예측
        
        Args:
            text: 분석할 텍스트
            max_length: 최대 토큰 길이
        
        Returns:
            {
                'intensity_level': str,  # "LOW", "MEDIUM", "HIGH"
                'intensity_level_confidence': float,  # 0.0-1.0
                'probabilities': {
                    'LOW': float,
                    'MEDIUM': float,
                    'HIGH': float
                }
            }
        """
        if self.model is None or self.tokenizer is None:
            return {
                'intensity_level': 'LOW',
                'intensity_level_confidence': 0.0,
                'probabilities': {'LOW': 1.0, 'MEDIUM': 0.0, 'HIGH': 0.0}
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
                logits = outputs.logits
                
                # Softmax로 확률 계산
                probabilities = torch.softmax(logits, dim=-1)
                predicted_idx = torch.argmax(probabilities, dim=-1).item()
                confidence = probabilities[0][predicted_idx].item()
                
                # Label 이름 변환
                intensity_level = self.LABEL_MAPPING.get(predicted_idx, 'LOW')
                
                # 확률 분포 생성
                label_probs = {}
                for idx, label in self.LABEL_MAPPING.items():
                    if idx < probabilities.size(1):
                        label_probs[label] = probabilities[0][idx].item()
                    else:
                        label_probs[label] = 0.0
            
            return {
                'intensity_level': intensity_level,
                'intensity_level_confidence': float(confidence),
                'probabilities': label_probs
            }
        except Exception as e:
            warnings.warn(f"3진 분류 예측 실패: {e}")
            return {
                'intensity_level': 'LOW',
                'intensity_level_confidence': 0.0,
                'probabilities': {'LOW': 1.0, 'MEDIUM': 0.0, 'HIGH': 0.0}
            }
    
    def is_available(self) -> bool:
        """모델 사용 가능 여부"""
        return self.model is not None and self.tokenizer is not None

