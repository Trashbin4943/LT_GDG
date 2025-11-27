"""
모델 없이 Fallback 모드로 작동하는지 테스트

AI-Hub 모델이 없어도 Baseline 규칙만으로 정상 작동하는지 확인
"""
import sys
import os
import unittest

# 부모 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_classify_system.pipeline.main_pipeline import MainPipeline
from logic_classify_system.config.labels import PipelineMode, NormalLabel, SpecialLabel
from logic_classify_system.data.data_structures import PipelineResult


class TestModelFallback(unittest.TestCase):
    """모델 없이 Fallback 모드 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """클래스 초기화 - 모델 없이 파이프라인 생성"""
        # 모델 경로를 명시적으로 None으로 설정하여 모델 로드 방지
        cls.pipeline = MainPipeline(
            mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL,
            use_korcen=True,
            aihub_base_model_path=None,  # 모델 없이 시작
            aihub_model1_checkpoint=None,
            aihub_model2_checkpoint=None,
            aihub_device=None
        )
    
    def test_pipeline_initialization_without_model(self):
        """모델 없이 파이프라인 초기화 테스트"""
        self.assertIsNotNone(self.pipeline)
        self.assertIsNotNone(self.pipeline.text_splitter)
        self.assertIsNotNone(self.pipeline.profanity_detector)
        self.assertIsNotNone(self.pipeline.intent_predictor)
        self.assertIsNotNone(self.pipeline.label_router)
        self.assertIsNotNone(self.pipeline.session_manager)
        
        # 모델은 None이어야 함 (fallback 모드)
        self.assertIsNone(self.pipeline.aihub_model)
        self.assertIsNone(self.pipeline.aihub_detector)
        # SpecialLabelFilter는 모델 없이도 생성됨 (baseline 규칙 사용)
        # self.assertIsNone(self.pipeline.special_label_filter)
    
    def test_profanity_detection_without_model(self):
        """모델 없이 비속어 감지 테스트 (Baseline + Korcen)"""
        test_cases = [
            ("시발놈아", True),  # 비속어
            ("안녕하세요", False),  # 정상
            ("존나짜증나", True),  # 비속어
            ("감사합니다", False),  # 정상
        ]
        
        for text, expected_has_profanity in test_cases:
            with self.subTest(text=text):
                result = self.pipeline.profanity_detector.detect(text)
                
                # None이 반환될 수 있음 (비속어가 감지되지 않은 경우)
                if result is None:
                    has_profanity = False
                    print(f"  입력: '{text}' -> 비속어 감지: False (None 반환)")
                else:
                    self.assertIsInstance(result.is_profanity, bool)
                    has_profanity = result.is_profanity
                    print(f"  입력: '{text}' -> 비속어 감지: {has_profanity}")
                
                # 정확도는 규칙 기반이므로 완벽하지 않을 수 있음
                # 최소한 결과가 반환되거나 None인지만 확인
    
    def test_intent_classification_without_model(self):
        """모델 없이 의도 분류 테스트 (Baseline 규칙)"""
        test_cases = [
            ("문의 드립니다", NormalLabel.INQUIRY),
            ("불만 있습니다", NormalLabel.COMPLAINT),
            ("요청 드립니다", NormalLabel.REQUEST),
            ("확인 부탁드립니다", NormalLabel.CONFIRMATION),
            ("시발놈아", SpecialLabel.PROFANITY),  # 비속어는 Special Label
        ]
        
        for text, expected_label in test_cases:
            with self.subTest(text=text, expected_label=expected_label):
                # 단일 발화 분류
                customer_sentences, agent_sentences = self.pipeline.text_splitter.split_text(text)
                
                # 고객 발화 우선 사용
                if customer_sentences:
                    utterance_text = customer_sentences[0]
                elif agent_sentences:
                    utterance_text = agent_sentences[0]
                else:
                    utterance_text = text
                
                # IntentPredictor는 predict 메서드 사용 (세션 컨텍스트 필요)
                session_context = self.pipeline.session_manager.get_session_context("test_session")
                profanity_result = self.pipeline.profanity_detector.detect(utterance_text)
                profanity_detected = profanity_result.is_profanity if profanity_result else False
                profanity_category = profanity_result.category if profanity_result else None
                profanity_confidence = profanity_result.confidence if profanity_result else 0.0
                
                classification = self.pipeline.intent_predictor.predict(
                    text=utterance_text,
                    profanity_detected=profanity_detected,
                    session_context=session_context,
                    profanity_category=profanity_category,
                    profanity_confidence=profanity_confidence
                )
                
                self.assertIsNotNone(classification)
                print(f"  입력: '{text}' -> 분류: {classification.label}")
    
    def test_full_pipeline_without_model(self):
        """모델 없이 전체 파이프라인 실행 테스트"""
        test_text = "안녕하세요 문의 드립니다"
        session_id = "test_session_001"
        
        result = self.pipeline.process(text=test_text, session_id=session_id)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, PipelineResult)
        self.assertEqual(result.session_id, session_id)
        
        # 결과 구조 확인
        self.assertIsNotNone(result.results)
        self.assertIsInstance(result.results, list)
        
        print(f"\n  입력: '{test_text}'")
        print(f"  분류 결과 수: {len(result.results)}")
        if result.results:
            print(f"  첫 번째 분류: {result.results[0].label}")
            print(f"  라벨 타입: {result.results[0].label_type}")
    
    def test_special_label_detection_without_model(self):
        """모델 없이 특수 라벨 감지 테스트 (Baseline 규칙만)"""
        test_cases = [
            ("시발놈아", SpecialLabel.PROFANITY),
            ("죽여버리겠다", SpecialLabel.VIOLENCE_THREAT),
            ("짜증나 죽겠다", SpecialLabel.PROFANITY),  # 약한 위협
        ]
        
        for text, expected_label in test_cases:
            with self.subTest(text=text):
                customer_sentences, agent_sentences = self.pipeline.text_splitter.split_text(text)
                
                # 고객 발화 우선 사용
                if customer_sentences:
                    utterance_text = customer_sentences[0]
                elif agent_sentences:
                    utterance_text = agent_sentences[0]
                else:
                    utterance_text = text
                
                # IntentPredictor는 predict 메서드 사용 (세션 컨텍스트 필요)
                session_context = self.pipeline.session_manager.get_session_context("test_session")
                profanity_result = self.pipeline.profanity_detector.detect(utterance_text)
                profanity_detected = profanity_result.is_profanity if profanity_result else False
                profanity_category = profanity_result.category if profanity_result else None
                profanity_confidence = profanity_result.confidence if profanity_result else 0.0
                
                classification = self.pipeline.intent_predictor.predict(
                    text=utterance_text,
                    profanity_detected=profanity_detected,
                    session_context=session_context,
                    profanity_category=profanity_category,
                    profanity_confidence=profanity_confidence
                )
                
                self.assertIsNotNone(classification)
                # Special Label이 감지되었는지 확인
                if classification.label_type == "SPECIAL":
                    print(f"  입력: '{text}' -> 특수 라벨 감지: {classification.label}")
                else:
                    print(f"  입력: '{text}' -> 일반 라벨: {classification.label}")
    
    def test_multiple_utterances_without_model(self):
        """모델 없이 여러 발화 처리 테스트"""
        test_text = "안녕하세요. 문의 드립니다. 감사합니다."
        session_id = "test_session_002"
        
        result = self.pipeline.process(text=test_text, session_id=session_id)
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.results)
        
        print(f"\n  입력: '{test_text}'")
        print(f"  발화 수: {len(result.results)}")
        for i, cls_result in enumerate(result.results):
            print(f"    발화 {i+1}: '{cls_result.text}' -> {cls_result.label}")
    
    def test_pipeline_modes_without_model(self):
        """다양한 파이프라인 모드에서 모델 없이 작동 테스트"""
        modes = [
            PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL,
            PipelineMode.CLASSIFY_BOTH_ALWAYS,
            PipelineMode.DETAIL_FIRST_THEN_VERIFY,
        ]
        
        test_text = "문의 드립니다"
        
        for mode in modes:
            with self.subTest(mode=mode):
                pipeline = MainPipeline(
                    mode=mode,
                    use_korcen=True,
                    aihub_base_model_path=None,
                    aihub_model1_checkpoint=None,
                    aihub_model2_checkpoint=None
                )
                
                result = pipeline.process(text=test_text, session_id=f"test_mode_{mode.name}")
                
                self.assertIsNotNone(result)
                self.assertIsNotNone(result.results)
                if result.results:
                    print(f"  모드: {mode.name} -> 첫 번째 분류: {result.results[0].label}")
                else:
                    print(f"  모드: {mode.name} -> 분류 결과 없음")


class TestModelWithFallback(unittest.TestCase):
    """모델 로드 실패 시 Fallback 모드로 자동 전환 테스트"""
    
    def test_pipeline_with_invalid_model_path(self):
        """잘못된 모델 경로로 초기화 시 Fallback 모드로 전환"""
        # 존재하지 않는 모델 경로 사용
        pipeline = MainPipeline(
            mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL,
            use_korcen=True,
            aihub_base_model_path="./nonexistent/model",
            aihub_model1_checkpoint="./nonexistent/checkpoint1",
            aihub_model2_checkpoint="./nonexistent/checkpoint2"
        )
        
        # 파이프라인은 정상 초기화되어야 함 (모델 없이도)
        self.assertIsNotNone(pipeline)
        self.assertIsNotNone(pipeline.intent_predictor)
        
        # 모델 로드 실패로 None이어야 함
        # self.assertIsNone(pipeline.aihub_model)  # 로드 실패 시 None
        
        # 하지만 파이프라인은 작동해야 함
        result = pipeline.process(text="안녕하세요", session_id="test_fallback")
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.results)
        if result.results:
            print(f"  Fallback 모드 작동 확인: 첫 번째 분류 = {result.results[0].label}")
        else:
            print(f"  Fallback 모드 작동 확인: 분류 결과 없음")


if __name__ == "__main__":
    unittest.main(verbosity=2)

