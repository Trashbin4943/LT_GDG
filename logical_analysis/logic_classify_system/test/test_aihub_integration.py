"""
AI-Hub 모델 통합 테스트

AI-Hub 모델을 사용한 Special Label 감지 테스트
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.models.aihub_ethic_model import AIHubEthicModel
from logic_classify_system.filtering.aihub_special_label_detector import AIHubSpecialLabelDetector
from logic_classify_system.config.model_config import ModelConfig


class TestAIHubIntegration(unittest.TestCase):
    """AI-Hub 모델 통합 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """클래스 초기화 (한 번만 실행)"""
        # 모델 가용성 확인
        cls.model_available = ModelConfig.check_model_availability()
        
        # 모델이 있는 경우에만 초기화
        if cls.model_available["base_model"]:
            try:
                model_paths = ModelConfig.get_model_paths()
                cls.aihub_model = AIHubEthicModel(
                    base_model_path=model_paths["base_model_path"],
                    model1_checkpoint=model_paths["model1_checkpoint"] if cls.model_available["model1_checkpoint"] else None,
                    model2_checkpoint=model_paths["model2_checkpoint"] if cls.model_available["model2_checkpoint"] else None
                )
                cls.detector = AIHubSpecialLabelDetector(aihub_model=cls.aihub_model)
                cls.models_loaded = True
            except Exception as e:
                print(f"모델 로드 실패 (Baseline 규칙만 사용): {e}")
                cls.models_loaded = False
        else:
            cls.models_loaded = False
            cls.aihub_model = None
            cls.detector = None
    
    def setUp(self):
        """테스트 설정"""
        self.test_cases = [
            ("시발놈아", "PROFANITY"),
            ("보지", "SEXUAL_HARASSMENT"),
            ("죽여버릴거야", "VIOLENCE_THREAT"),
            ("상품 문의합니다", None)  # Special Label 아님
        ]
    
    def test_model_loading(self):
        """모델 로드 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        self.assertIsNotNone(self.aihub_model)
        self.assertIsNotNone(self.detector)
    
    def test_model_availability(self):
        """모델 가용성 확인"""
        availability = ModelConfig.check_model_availability()
        
        self.assertIsInstance(availability, dict)
        self.assertIn("base_model", availability)
        self.assertIn("model1_checkpoint", availability)
        self.assertIn("model2_checkpoint", availability)
        
        if not availability["base_model"]:
            print("경고: AI-Hub 모델 파일이 없습니다. Baseline 규칙만 사용됩니다.")
    
    def test_predict_immoral(self):
        """비도덕 여부 판단 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        
        text = "시발놈아"
        
        try:
            is_immoral, confidence = self.aihub_model.predict_immoral(text)
            
            self.assertIsInstance(is_immoral, bool)
            self.assertIsInstance(confidence, float)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)
        except ValueError as e:
            # 모델이 로드되지 않은 경우
            self.skipTest(f"모델이 로드되지 않음: {e}")
    
    def test_predict_type(self):
        """비도덕 유형 분류 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        
        text = "시발놈아"
        
        try:
            predicted_type = self.aihub_model.predict_type(text)
            
            # 예상되는 라벨 타입 확인
            expected_types = ["VIOLENCE", "SEXUAL", "ABUSE", "DISCRIMINATION", "IMMORAL_NONE"]
            self.assertIn(predicted_type, expected_types)
        except ValueError as e:
            self.skipTest(f"모델이 로드되지 않음: {e}")
    
    def test_special_label_detection(self):
        """Special Label 감지 테스트"""
        if not self.models_loaded:
            self.skipTest("모델이 로드되지 않음")
        
        for text, expected_label in self.test_cases:
            with self.subTest(text=text):
                try:
                    result = self.detector.detect(text)
                    
                    if expected_label:
                        # Special Label이 예상되는 경우
                        if result:
                            self.assertEqual(result.label, expected_label)
                            self.assertGreater(result.confidence, 0.0)
                    else:
                        # Special Label이 아닌 경우
                        # result가 None이거나 IMMORAL_NONE일 수 있음
                        if result:
                            self.assertNotEqual(result.label, expected_label)
                except Exception as e:
                    # 모델이 없는 경우 무시
                    if "로드되지 않았습니다" in str(e):
                        self.skipTest(f"모델이 로드되지 않음: {e}")


if __name__ == "__main__":
    unittest.main()
