"""
텍스트 윤리검증 데이터셋 검증

데이터셋 형식 및 라벨 검증
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.config.labels import SpecialLabel, NormalLabel, LabelType
from logic_classify_system.data.data_structures import (
    ClassificationResult,
    SpecialLabelDetectionResult
)


class TestEthicsDatasetValidation(unittest.TestCase):
    """텍스트 윤리검증 데이터셋 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 테스트 케이스 (텍스트, 예상 라벨, 라벨 타입)
        self.test_cases = [
            ("시발놈아", "PROFANITY", "SPECIAL"),
            ("보지", "SEXUAL_HARASSMENT", "SPECIAL"),
            ("죽여버릴거야", "VIOLENCE_THREAT", "SPECIAL"),
            ("짱깨", "HATE_SPEECH", "SPECIAL"),
            ("지금 당장 환불해줘", "UNREASONABLE_DEMAND", "SPECIAL"),
            ("상품 문의합니다", "INQUIRY", "NORMAL"),
            ("서비스가 불만족스럽습니다", "COMPLAINT", "NORMAL"),
            ("환불해주세요", "REQUEST", "NORMAL")
        ]
    
    def test_special_label_enum(self):
        """Special Label Enum 검증"""
        # 모든 Special Label이 정의되어 있는지 확인
        expected_labels = [
            "VIOLENCE_THREAT",
            "SEXUAL_HARASSMENT",
            "PROFANITY",
            "HATE_SPEECH",
            "UNREASONABLE_DEMAND",
            "REPETITION"
        ]
        
        for label_str in expected_labels:
            label = SpecialLabel.from_string(label_str)
            self.assertIsNotNone(label, f"Special Label '{label_str}'이 정의되지 않았습니다")
    
    def test_normal_label_enum(self):
        """Normal Label Enum 검증"""
        # 모든 Normal Label이 정의되어 있는지 확인
        expected_labels = [
            "INQUIRY",
            "COMPLAINT",
            "REQUEST",
            "CLARIFICATION",
            "CONFIRMATION",
            "CLOSING"
        ]
        
        for label_str in expected_labels:
            label = NormalLabel.from_string(label_str)
            self.assertIsNotNone(label, f"Normal Label '{label_str}'이 정의되지 않았습니다")
    
    def test_label_type_enum(self):
        """Label Type Enum 검증"""
        # 모든 Label Type이 정의되어 있는지 확인
        expected_types = ["SPECIAL", "NORMAL", "UNKNOWN"]
        
        for type_str in expected_types:
            try:
                label_type = LabelType(type_str)
                self.assertIsNotNone(label_type, f"Label Type '{type_str}'이 정의되지 않았습니다")
            except ValueError:
                self.fail(f"Label Type '{type_str}'이 정의되지 않았습니다")
    
    def test_classification_result_structure(self):
        """ClassificationResult 구조 검증"""
        result = ClassificationResult(
            label="PROFANITY",
            label_type="SPECIAL",
            confidence=0.85,
            text="시발놈아"
        )
        
        self.assertEqual(result.label, "PROFANITY")
        self.assertEqual(result.label_type, "SPECIAL")
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.text, "시발놈아")
        self.assertIsInstance(result.label, str)
        self.assertIsInstance(result.label_type, str)
        self.assertIsInstance(result.confidence, float)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
    
    def test_special_label_detection_result_structure(self):
        """SpecialLabelDetectionResult 구조 검증"""
        result = SpecialLabelDetectionResult(
            label="PROFANITY",
            confidence=0.85,
            severity="HIGH",
            detection_method="aihub_model",
            text="시발놈아"
        )
        
        self.assertEqual(result.label, "PROFANITY")
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.severity, "HIGH")
        self.assertEqual(result.detection_method, "aihub_model")
        self.assertIn(result.severity, ["LOW", "MEDIUM", "HIGH"])
        self.assertIn(result.detection_method, ["aihub_model", "baseline", "routed"])
    
    def test_label_mapping(self):
        """라벨 매핑 검증"""
        # Special Label 값 확인
        special_labels = SpecialLabel.values()
        self.assertIn("PROFANITY", special_labels)
        self.assertIn("VIOLENCE_THREAT", special_labels)
        self.assertIn("SEXUAL_HARASSMENT", special_labels)
        
        # Normal Label 값 확인
        normal_labels = NormalLabel.values()
        self.assertIn("INQUIRY", normal_labels)
        self.assertIn("COMPLAINT", normal_labels)
        self.assertIn("REQUEST", normal_labels)
    
    def test_data_structures_import(self):
        """데이터 구조 import 검증"""
        from logic_classify_system.data.data_structures import (
            ProfanityResult,
            ClassificationResult,
            SpecialLabelDetectionResult,
            FilteringResult,
            EvaluationResult,
            RouterResult,
            PipelineResult
        )
        
        # 모든 데이터 구조가 import 가능한지 확인
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
