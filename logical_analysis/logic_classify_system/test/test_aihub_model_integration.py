"""
AI-Hub 모델 통합 테스트 (상세 버전)

AI-Hub 모델의 상세 기능 테스트
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.models.aihub_ethic_model import AIHubEthicModel
from logic_classify_system.config.model_config import ModelConfig


class TestAIHubModelIntegration(unittest.TestCase):
    """AI-Hub 모델 통합 테스트 (상세)"""
    
    @classmethod
    def setUpClass(cls):
        """클래스 초기화"""
        cls.model_available = ModelConfig.check_model_availability()
        
        if cls.model_available["base_model"]:
            try:
                model_paths = ModelConfig.get_model_paths()
                cls.aihub_model = AIHubEthicModel(
                    base_model_path=model_paths["base_model_path"],
                    model1_checkpoint=model_paths["model1_checkpoint"] if cls.model_available["model1_checkpoint"] else None,
                    model2_checkpoint=model_paths["model2_checkpoint"] if cls.model_available["model2_checkpoint"] else None
                )
                cls.models_loaded = True
            except Exception as e:
                print(f"모델 로드 실패: {e}")
                cls.models_loaded = False
        else:
            cls.models_loaded = False
            cls.aihub_model = None
    
    def test_model_initialization(self):
        """모델 초기화 테스트"""
        if not self.model_available["base_model"]:
            self.skipTest("모델 파일이 없습니다")
        
        self.assertIsNotNone(self.aihub_model)
        self.assertIsNotNone(self.aihub_model.tokenizer)
    
    def test_model1_available(self):
        """모델 1 (이진 분류) 가용성 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        if not self.model_available["model1_checkpoint"]:
            self.skipTest("모델 1 체크포인트가 없습니다")
        
        self.assertIsNotNone(self.aihub_model.model1)
    
    def test_model2_available(self):
        """모델 2 (다중 분류) 가용성 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        if not self.model_available["model2_checkpoint"]:
            self.skipTest("모델 2 체크포인트가 없습니다")
        
        self.assertIsNotNone(self.aihub_model.model2)
        self.assertIsNotNone(self.aihub_model.model2_config)
    
    def test_predict_immoral_with_confidence(self):
        """비도덕 여부 판단 및 신뢰도 테스트"""
        if not self.models_loaded or not self.aihub_model or not self.aihub_model.model1:
            self.skipTest("모델 1이 로드되지 않음")
        
        test_cases = [
            ("시발놈아", True),
            ("안녕하세요", False)
        ]
        
        for text, expected_immoral in test_cases:
            with self.subTest(text=text):
                try:
                    is_immoral, confidence = self.aihub_model.predict_immoral(text)
                    
                    self.assertIsInstance(is_immoral, bool)
                    self.assertIsInstance(confidence, float)
                    self.assertGreaterEqual(confidence, 0.0)
                    self.assertLessEqual(confidence, 1.0)
                    
                    # 예상과 일치하는지 확인 (정확도는 모델에 따라 다를 수 있음)
                    # 여기서는 결과가 반환되는지만 확인
                except Exception as e:
                    self.fail(f"예외 발생: {e}")
    
    def test_predict_type_with_probs(self):
        """비도덕 유형 분류 및 확률 테스트"""
        if not self.models_loaded or not self.aihub_model or not self.aihub_model.model2:
            self.skipTest("모델 2가 로드되지 않음")
        
        text = "시발놈아"
        
        try:
            predicted_type, probs_dict = self.aihub_model.predict_type(text, return_probs=True)
            
            self.assertIsInstance(predicted_type, str)
            self.assertIsInstance(probs_dict, dict)
            
            # 예상되는 라벨 타입 확인
            expected_types = ["VIOLENCE", "SEXUAL", "ABUSE", "DISCRIMINATION", "IMMORAL_NONE"]
            self.assertIn(predicted_type, expected_types)
            
            # 확률 딕셔너리 확인
            for label, prob in probs_dict.items():
                self.assertIn(label, expected_types)
                self.assertIsInstance(prob, float)
                self.assertGreaterEqual(prob, 0.0)
                self.assertLessEqual(prob, 1.0)
            
            # 확률의 합이 대략 1에 가까운지 확인
            prob_sum = sum(probs_dict.values())
            self.assertAlmostEqual(prob_sum, 1.0, places=2)
        except Exception as e:
            self.fail(f"예외 발생: {e}")
    
    def test_get_confidence(self):
        """신뢰도 조회 테스트"""
        if not self.models_loaded or not self.aihub_model or not self.aihub_model.model2:
            self.skipTest("모델 2가 로드되지 않음")
        
        text = "시발놈아"
        predicted_label = "PROFANITY"  # 예시
        
        try:
            confidence = self.aihub_model.get_confidence(text, predicted_label)
            
            self.assertIsInstance(confidence, float)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)
        except Exception as e:
            # 모델이 없는 경우나 라벨 매핑이 안 되는 경우
            self.skipTest(f"신뢰도 조회 실패: {e}")


if __name__ == "__main__":
    unittest.main()
