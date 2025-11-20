"""
AI-Hub 윤리 검증 모델 래퍼

모델 로드 및 추론만 담당 (독립책임원칙)
"""
from typing import Tuple, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

# PyTorch와 Transformers 가용성 확인
try:
    import torch
    from transformers import BertForSequenceClassification, BertTokenizer, BertConfig
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch와 Transformers가 설치되지 않았습니다. pip install torch transformers를 실행하세요.")


class AIHubEthicModel:
    """
    AI-Hub 윤리 검증 모델 래퍼
    
    책임: 모델 로드 및 추론만 담당
    - 모델 1: 이진 분류 (True/False)
    - 모델 2: 5개 클래스 분류 (VIOLENCE, SEXUAL, ABUSE, DISCRIMINATION, IMMORAL_NONE)
    """
    
    def __init__(
        self,
        base_model_path: str = "./model",
        model1_checkpoint: Optional[str] = None,
        model2_checkpoint: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        모델 초기화
        
        Args:
            base_model_path: deeqBERT-base 모델 경로 (./model)
            model1_checkpoint: 모델 1 체크포인트 경로 (ckpt/class/checkpoint-XXXX)
            model2_checkpoint: 모델 2 체크포인트 경로 (ckpt/multi/checkpoint-XXXX)
            device: 사용할 디바이스 ("cuda" or "cpu"), None이면 자동 선택
        """
        self.base_model_path = base_model_path
        self.model1_checkpoint = model1_checkpoint
        self.model2_checkpoint = model2_checkpoint
        
        # 디바이스 설정
        if device is None:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device
        
        logger.info(f"모델 디바이스: {self.device}")
        
        # 토크나이저 로드
        self.tokenizer = None
        if TORCH_AVAILABLE:
            try:
                tokenizer_path = os.path.join(base_model_path, "tokenizer")
                if os.path.exists(tokenizer_path):
                    self.tokenizer = BertTokenizer.from_pretrained(tokenizer_path, do_lower_case=True)
                else:
                    self.tokenizer = BertTokenizer.from_pretrained(base_model_path, do_lower_case=True)
                logger.info(f"토크나이저 로드 완료: {base_model_path}")
            except Exception as e:
                logger.error(f"토크나이저 로드 실패: {e}")
                self.tokenizer = None
        
        # 모델 1 로드 (이진 분류)
        self.model1 = None
        if model1_checkpoint and TORCH_AVAILABLE:
            try:
                config = BertConfig.from_pretrained(model1_checkpoint)
                config.num_labels = 2
                self.model1 = BertForSequenceClassification.from_pretrained(
                    model1_checkpoint, config=config
                )
                self.model1.to(self.device)
                self.model1.eval()
                logger.info(f"모델 1 로드 완료: {model1_checkpoint}")
            except Exception as e:
                logger.error(f"모델 1 로드 실패: {e}")
                self.model1 = None
        
        # 모델 2 로드 (5개 클래스 분류)
        self.model2 = None
        self.model2_config = None
        if model2_checkpoint and TORCH_AVAILABLE:
            try:
                config = BertConfig.from_pretrained(model2_checkpoint)
                # 모델 2 라벨: VIOLENCE, SEXUAL, ABUSE, DISCRIMINATION, IMMORAL_NONE
                config.num_labels = 5
                config.id2label = {
                    0: "VIOLENCE",
                    1: "SEXUAL",
                    2: "ABUSE",
                    3: "DISCRIMINATION",
                    4: "IMMORAL_NONE"
                }
                config.label2id = {v: k for k, v in config.id2label.items()}
                self.model2_config = config
                
                self.model2 = BertForSequenceClassification.from_pretrained(
                    model2_checkpoint, config=config
                )
                self.model2.to(self.device)
                self.model2.eval()
                logger.info(f"모델 2 로드 완료: {model2_checkpoint}")
            except Exception as e:
                logger.error(f"모델 2 로드 실패: {e}")
                self.model2 = None
    
    def predict_immoral(self, text: str) -> Tuple[bool, float]:
        """
        비도덕 여부 판단 (모델 1)
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            (is_immoral, confidence)
            - is_immoral: True (비도덕) 또는 False (비도덕 아님)
            - confidence: 신뢰도 (0.0-1.0)
        
        Raises:
            ValueError: 모델 1이 로드되지 않은 경우
        """
        if self.model1 is None:
            raise ValueError("모델 1이 로드되지 않았습니다.")
        
        if not TORCH_AVAILABLE:
            return (False, 0.5)
        
        if self.tokenizer is None:
            return (False, 0.5)
        
        # 토크나이징
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)
        
        # 추론
        with torch.no_grad():
            outputs = self.model1(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            probs = probs.cpu().numpy()[0]
        
        # 결과 (label 1 = True = 비도덕)
        is_immoral = probs[1] > probs[0]
        confidence = float(probs[1] if is_immoral else probs[0])
        
        return (is_immoral, confidence)
    
    def predict_type(self, text: str, return_probs: bool = False):
        """
        비도덕 유형 분류 (모델 2)
        
        Args:
            text: 분석할 텍스트
            return_probs: 확률도 반환할지 여부
        
        Returns:
            예측된 라벨 (단일 값) 또는 (라벨, 확률 딕셔너리)
        
        Raises:
            ValueError: 모델 2가 로드되지 않은 경우
        """
        if self.model2 is None:
            raise ValueError("모델 2가 로드되지 않았습니다.")
        
        if not TORCH_AVAILABLE:
            return "IMMORAL_NONE"
        
        if self.tokenizer is None:
            return "IMMORAL_NONE"
        
        # 토크나이징
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)
        
        # 추론
        with torch.no_grad():
            outputs = self.model2(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            probs = probs.cpu().numpy()[0]
        
        # 예측된 라벨
        predicted_idx = int(probs.argmax())
        predicted_label = self.model2_config.id2label[predicted_idx]
        
        if return_probs:
            # 확률 딕셔너리 생성
            probs_dict = {
                self.model2_config.id2label[i]: float(probs[i])
                for i in range(len(probs))
            }
            return (predicted_label, probs_dict)
        
        return predicted_label
    
    def get_confidence(self, text: str, predicted_label: str) -> float:
        """
        예측된 라벨에 대한 신뢰도 반환
        
        Args:
            text: 분석할 텍스트
            predicted_label: 예측된 라벨
        
        Returns:
            신뢰도 (0.0-1.0)
        
        Raises:
            ValueError: 모델 2가 로드되지 않은 경우
        """
        _, probs_dict = self.predict_type(text, return_probs=True)
        return probs_dict.get(predicted_label, 0.0)

