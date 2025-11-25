"""
문장 분류 모델 (KoBERT/KoSentenceBERT 기반)

학습된 모델을 사용하여 발화를 분류하는 클래스
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoConfig
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("transformers 라이브러리가 설치되지 않았습니다. 모델 분류기를 사용할 수 없습니다.")


class SentenceClassifier:
    """문장 분류 모델"""
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True):
        """
        문장 분류기 초기화
        
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
            # 기본 모델 경로 (현재 프로젝트의 models 디렉토리)
            current_dir = Path(__file__).parent.parent
            model_path = str(current_dir / 'models' / 'aihub' / 'base_model')
        
        self.model_path = Path(model_path)
        
        # GPU 설정
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
            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            
            # 모델 설정 로드
            try:
                config = AutoConfig.from_pretrained(str(self.model_path))
            except:
                # 설정 파일이 없으면 기본값 사용
                config = None
            
            # 모델 로드
            if config:
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(self.model_path),
                    config=config
                )
            else:
                # pytorch_model.bin만 있는 경우
                # 기본 모델 구조를 사용 (num_labels는 추론하거나 기본값 사용)
                try:
                    self.model = AutoModelForSequenceClassification.from_pretrained(
                        str(self.model_path)
                    )
                except Exception as e:
                    warnings.warn(f"모델 로드 실패: {e}")
                    self.model = None
                    self.tokenizer = None
                    return
            
            # GPU로 이동
            if self.model:
                self.model = self.model.to(self.device)
                self.model.eval()
                print(f"모델 로드 완료: {self.model_path} (장치: {self.device})")
        
        except Exception as e:
            warnings.warn(f"모델 로드 중 오류 발생: {e}")
            self.model = None
            self.tokenizer = None
    
    def predict(
        self,
        text: str,
        max_length: int = 128,
        return_probabilities: bool = True
    ) -> Dict[str, any]:
        """
        문장 분류 예측
        
        Args:
            text: 분류할 텍스트
            max_length: 최대 토큰 길이
            return_probabilities: 확률 분포 반환 여부
        
        Returns:
            {
                'label': str,           # 분류된 Label
                'confidence': float,    # 신뢰도 (0.0-1.0)
                'probabilities': Dict[str, float],  # 각 Label별 확률 (선택사항)
                'label_type': str       # "NORMAL" or "SPECIAL"
            }
        """
        if self.model is None or self.tokenizer is None:
            # 모델이 없으면 기본값 반환
            return {
                'label': 'INQUIRY',
                'confidence': 0.3,
                'probabilities': {'INQUIRY': 1.0},
                'label_type': 'NORMAL'
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
                
                # 로짓 추출
                logits = outputs.logits
                
                # 확률 계산 (Softmax)
                if logits.dim() > 1 and logits.size(1) > 1:
                    # Multi-class classification
                    probabilities = torch.softmax(logits, dim=-1)
                    predicted_idx = torch.argmax(probabilities, dim=-1).item()
                    confidence = probabilities[0][predicted_idx].item()
                    
                    # Label ID를 Label 이름으로 변환
                    predicted_label = self._id_to_label(predicted_idx)
                    
                    # 확률 분포 생성
                    label_probs = {}
                    for idx in range(probabilities.size(1)):
                        label = self._id_to_label(idx)
                        label_probs[label] = probabilities[0][idx].item()
                else:
                    # Binary classification or Regression
                    # 기본값 반환 (모델 출력 형태에 따라 수정 필요)
                    predicted_label = 'INQUIRY'
                    confidence = 0.5
                    label_probs = {'INQUIRY': 0.5}
            
            # Label 타입 결정
            label_type = self._determine_label_type(predicted_label)
            
            result = {
                'label': predicted_label,
                'confidence': confidence,
                'label_type': label_type
            }
            
            if return_probabilities:
                result['probabilities'] = label_probs
            
            return result
        
        except Exception as e:
            warnings.warn(f"예측 중 오류 발생: {e}")
            return {
                'label': 'INQUIRY',
                'confidence': 0.3,
                'probabilities': {'INQUIRY': 1.0},
                'label_type': 'NORMAL'
            }
    
    def _id_to_label(self, label_id: int) -> str:
        """
        Label ID를 Label 이름으로 변환
        
        Args:
            label_id: Label ID
        
        Returns:
            Label 이름
        """
        # 모델의 Label ID 매핑 (모델에 따라 수정 필요)
        # 기본값: 모델 설정에서 확인하거나 직접 매핑
        label_mapping = {
            0: 'INQUIRY',
            1: 'COMPLAINT',
            2: 'REQUEST',
            3: 'CLARIFICATION',
            4: 'CONFIRMATION',
            5: 'CLOSING',
            6: 'PROFANITY',
            7: 'VIOLENCE_THREAT',
            8: 'SEXUAL_HARASSMENT',
            9: 'HATE_SPEECH',
            10: 'UNREASONABLE_DEMAND',
            11: 'REPETITION'
        }
        
        return label_mapping.get(label_id, 'INQUIRY')
    
    def _determine_label_type(self, label: str) -> str:
        """
        Label 타입 결정 (Normal or Special)
        
        Args:
            label: Label 이름
        
        Returns:
            "NORMAL" or "SPECIAL"
        """
        from ..config.labels import NORMAL_LABELS, SPECIAL_LABELS
        
        if label in NORMAL_LABELS:
            return "NORMAL"
        elif label in SPECIAL_LABELS:
            return "SPECIAL"
        else:
            return "UNKNOWN"
    
    def is_available(self) -> bool:
        """모델 사용 가능 여부"""
        return self.model is not None and self.tokenizer is not None

