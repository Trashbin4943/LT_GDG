"""
Mock 모델 클래스
테스트 환경에서 실제 모델 없이 테스트하기 위한 Mock 클래스
"""

from typing import Dict, Any
from pathlib import Path


class MockIntensityRegressionModel:
    """Intensity Regression 모델 Mock 클래스"""
    
    def __init__(self, model_path: str, use_gpu: bool = True):
        """
        Mock 모델 초기화
        
        Args:
            model_path: 모델 경로 (사용하지 않지만 인터페이스 일치를 위해 유지)
            use_gpu: GPU 사용 여부 (사용하지 않지만 인터페이스 일치를 위해 유지)
        """
        self.model_path = Path(model_path) if model_path else None
        self.device = "cpu"  # Mock에서는 항상 CPU
        self.model = "mock_model"  # 실제 모델 대신 문자열
        self.tokenizer = "mock_tokenizer"
    
    def predict(self, text: str, max_length: int = 128) -> Dict[str, Any]:
        """
        Mock 예측 (고정값 반환)
        
        Args:
            text: 분석할 텍스트
            max_length: 최대 토큰 길이 (사용하지 않음)
        
        Returns:
            Mock 예측 결과
        """
        # 텍스트 내용에 따라 다른 intensity 반환 (테스트용)
        text_lower = text.lower()
        
        # 욕설이나 부정적 표현이 있으면 높은 intensity
        if any(word in text_lower for word in ['시발', '개새끼', '죽여', '끝장']):
            intensity = 2.5
        elif any(word in text_lower for word in ['불만', '환불', '보상']):
            intensity = 1.5
        elif any(word in text_lower for word in ['문의', '안녕', '감사']):
            intensity = 0.0
        else:
            intensity = 1.0
        
        is_immoral = intensity > 0.0
        immorality_confidence = min(intensity / 3.0, 1.0) if is_immoral else 0.0
        
        return {
            'intensity': float(intensity),
            'is_immoral': is_immoral,
            'immorality_confidence': float(immorality_confidence)
        }
    
    def is_available(self) -> bool:
        """Mock 모델은 항상 사용 가능"""
        return True


class MockTernaryClassificationModel:
    """3진 분류 모델 Mock 클래스"""
    
    LABEL_MAPPING = {
        0: 'LOW',
        1: 'MEDIUM',
        2: 'HIGH'
    }
    
    INTENSITY_RANGES = {
        'LOW': (1.0, 1.6),
        'MEDIUM': (1.8, 2.4),
        'HIGH': (2.6, 3.0)
    }
    
    def __init__(self, model_path: str, use_gpu: bool = True):
        """
        Mock 모델 초기화
        
        Args:
            model_path: 모델 경로 (사용하지 않지만 인터페이스 일치를 위해 유지)
            use_gpu: GPU 사용 여부 (사용하지 않지만 인터페이스 일치를 위해 유지)
        """
        self.model_path = Path(model_path) if model_path else None
        self.device = "cpu"  # Mock에서는 항상 CPU
        self.model = "mock_model"
        self.tokenizer = "mock_tokenizer"
    
    def predict(self, text: str, max_length: int = 128) -> Dict[str, Any]:
        """
        Mock 예측 (텍스트 내용에 따라 분류)
        
        Args:
            text: 분석할 텍스트
            max_length: 최대 토큰 길이 (사용하지 않음)
        
        Returns:
            Mock 예측 결과
        """
        text_lower = text.lower()
        
        # 텍스트 내용에 따라 intensity_level 결정
        if any(word in text_lower for word in ['시발', '개새끼', '죽여', '끝장', '참교육']):
            intensity_level = 'HIGH'
            confidence = 0.9
            probabilities = {'LOW': 0.05, 'MEDIUM': 0.05, 'HIGH': 0.9}
        elif any(word in text_lower for word in ['불만', '환불', '보상', '불편']):
            intensity_level = 'MEDIUM'
            confidence = 0.8
            probabilities = {'LOW': 0.1, 'MEDIUM': 0.8, 'HIGH': 0.1}
        elif any(word in text_lower for word in ['문의', '안녕', '감사', '확인']):
            intensity_level = 'LOW'
            confidence = 0.7
            probabilities = {'LOW': 0.7, 'MEDIUM': 0.2, 'HIGH': 0.1}
        else:
            intensity_level = 'LOW'
            confidence = 0.5
            probabilities = {'LOW': 0.5, 'MEDIUM': 0.3, 'HIGH': 0.2}
        
        return {
            'intensity_level': intensity_level,
            'intensity_level_confidence': float(confidence),
            'probabilities': probabilities
        }
    
    def is_available(self) -> bool:
        """Mock 모델은 항상 사용 가능"""
        return True

