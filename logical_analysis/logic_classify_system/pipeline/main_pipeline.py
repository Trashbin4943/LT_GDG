"""
메인 파이프라인 오케스트레이터

전체 파이프라인을 조율하여 문장 단위로 처리 (HEAD 기반)
전체 프로세스 조율, 세션 관리, 파이프라인 모드 제어 (logic 기능 통합)

재설계: 두 단계 세션 구조
1. BaselineValidationSession: baseline keyword 검증 + AI hub 모델 검증
2. IntensityValidationSession: special label만 intensity 검증
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..preprocessing.text_splitter import TextSplitter
from ..profanity_filter.profanity_detector import ProfanityDetector
from ..intent_classifier.intent_predictor import IntentPredictor
from ..intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor

# 새로운 세션 클래스 import
from .baseline_validation_session import BaselineValidationSession
from .intensity_validation_session import IntensityValidationSession
from .final_score_calculation_session import FinalScoreCalculationSession

# Feature Extractors (선택적 import)
try:
    from ..feature_extractor.customer_feature_extractor import CustomerFeatureExtractor
    from ..feature_extractor.agent_feature_extractor import AgentFeatureExtractor
except ImportError:
    CustomerFeatureExtractor = None
    AgentFeatureExtractor = None

from ..data.data_structures import (
    PipelineResult,
    ClassificationResult,
    RouterResult,
    ProfanityResult
)
from ..data.session_manager import SessionManager
from ..config.labels import PipelineMode, LabelType

# logic: 선택적 import
try:
    from ..labeling.label_router import LabelRouter
except ImportError:
    LabelRouter = None  # LabelRouter가 없을 경우 None으로 설정

logger = logging.getLogger(__name__)


class MainPipeline:
    """
    메인 파이프라인 (재설계: 두 단계 세션 구조)
    
    처리 흐름:
    1. BaselineValidationSession: baseline keyword 검증 + AI hub 모델 검증
    2. IntensityValidationSession: special label만 intensity 검증
    """
    
    def __init__(
        self,
        intensity_model_path: Optional[str] = None,
        ternary_model_path: Optional[str] = None,
        use_enhanced_predictor: bool = True,
        mode: Optional[PipelineMode] = None,
        use_korcen: bool = False,
        enable_routing: bool = False,  # logic: 라우팅 기능 활성화 여부
        # 새로운 세션 관련 파라미터
        use_two_stage_session: bool = True,  # 두 단계 세션 사용 여부
        aihub_base_path: Optional[str] = None,  # AI hub 모델 기본 경로
        aihub_model1_checkpoint: Optional[str] = None,  # AI hub 모델 1 체크포인트
        aihub_model2_checkpoint: Optional[str] = None  # AI hub 모델 2 체크포인트
    ):
        """
        파이프라인 초기화
        
        Args:
            intensity_model_path: Intensity Regression 모델 경로 (두 번째 세션용)
            ternary_model_path: Ternary Classification 모델 경로 (두 번째 세션용)
            use_enhanced_predictor: 향상된 예측기 사용 여부 (하위 호환성용, 기본: True)
            mode: 파이프라인 모드 (하위 호환성용)
            use_korcen: Korcen 사용 여부
            enable_routing: 라우팅 기능 활성화 여부 (logic: 추가)
            use_two_stage_session: 두 단계 세션 사용 여부 (기본: True)
            aihub_base_path: AI hub 모델 기본 경로
            aihub_model1_checkpoint: AI hub 모델 1 체크포인트 경로
            aihub_model2_checkpoint: AI hub 모델 2 체크포인트 경로
        """
        self.text_splitter = TextSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=use_korcen)
        self.use_two_stage_session = use_two_stage_session
        
        # 두 단계 세션 구조 사용
        if use_two_stage_session:
            # 첫 번째 세션: Baseline Validation Session
            self.baseline_session = BaselineValidationSession(
                aihub_base_path=aihub_base_path,
                aihub_model1_checkpoint=aihub_model1_checkpoint,
                aihub_model2_checkpoint=aihub_model2_checkpoint
            )
            
            # 두 번째 세션: Intensity Validation Session
            self.intensity_session = IntensityValidationSession(
                intensity_model_path=intensity_model_path,
                ternary_model_path=ternary_model_path
            )
            
            # 세 번째 세션: Final Score Calculation Session
            # Feature Extractor를 세션에 전달
            customer_feature_extractor = CustomerFeatureExtractor() if CustomerFeatureExtractor else None
            self.final_score_session = FinalScoreCalculationSession(
                use_feature_extractor=True,
                profanity_detector=self.profanity_detector,
                feature_extractor=customer_feature_extractor
            )
            
            # 기존 예측기는 하위 호환성을 위해 유지 (사용하지 않음)
            self.intent_predictor = None
        else:
            # 하위 호환성: 기존 방식 사용
            self.baseline_session = None
            self.intensity_session = None
            
            # HEAD: 향상된 의도 예측기 사용 (이중 모델 통합)
            if use_enhanced_predictor and (intensity_model_path or ternary_model_path):
                self.intent_predictor = EnhancedIntentPredictor(
                    intensity_model_path=intensity_model_path,
                    ternary_model_path=ternary_model_path,
                    use_models=True
                )
            else:
                # 기존 예측기 사용 (하위 호환성)
                # logic: PipelineMode 지원
                self.intent_predictor = IntentPredictor(
                    mode=mode or PipelineMode.default()
                )
        
        # HEAD: Feature Extractors (선택적)
        if CustomerFeatureExtractor:
            self.customer_feature_extractor = CustomerFeatureExtractor()
        else:
            self.customer_feature_extractor = None
        
        if AgentFeatureExtractor:
            self.agent_feature_extractor = AgentFeatureExtractor()
        else:
            self.agent_feature_extractor = None
        
        # HEAD: Session Manager
        self.session_manager = SessionManager()
        
        # logic: 라우팅 기능 (선택적)
        self.enable_routing = enable_routing
        self.label_router = None
        if enable_routing and LabelRouter:
            self.label_router = LabelRouter()
    
    def process(self, text: str, session_id: str) -> PipelineResult:
        """
        전체 파이프라인 실행 (재설계: 두 단계 세션 구조)
        
        Args:
            text: STT 결과 텍스트 (전체 대화)
            session_id: 세션 ID
        
        Returns:
            PipelineResult (전체 처리 결과)
        """
        # 두 단계 세션 구조 사용
        if self.use_two_stage_session:
            return self._process_two_stage(text, session_id)
        else:
            # 하위 호환성: 기존 방식
            return self._process_legacy(text, session_id)
    
    def _process_two_stage(self, text: str, session_id: str) -> PipelineResult:
        """
        두 단계 세션 구조로 처리
        
        Args:
            text: STT 결과 텍스트 (전체 대화)
            session_id: 세션 ID
        
        Returns:
            PipelineResult (전체 처리 결과)
        """
        # 1. 화자별 문장 분할 (고객/상담원 구분)
        customer_sentences, agent_sentences = self.text_splitter.split_by_speaker(text)
        
        # 2. 첫 번째 세션: Baseline Validation Session
        baseline_results = []
        
        for sentence in customer_sentences:
            # 1차: 욕설 필터링
            profanity_result = self.profanity_detector.detect(sentence)
            
            profanity_detected = profanity_result.is_profanity if profanity_result else False
            profanity_category = profanity_result.category if profanity_result else None
            profanity_confidence = profanity_result.confidence if profanity_result else 0.0
            
            # 첫 번째 세션: Baseline keyword 검증 + AI hub 모델 검증
            classification_result = self.baseline_session.validate(
                text=sentence,
                session_context=self.session_manager.get_context(session_id),
                profanity_detected=profanity_detected,
                profanity_category=profanity_category,
                profanity_confidence=profanity_confidence
            )
            
            baseline_results.append(classification_result)
            
            # 세션 맥락 업데이트
            self.session_manager.add_sentence(session_id, sentence)
        
        # 3. 두 번째 세션: Intensity Validation Session (Special Label만)
        intensity_validated_results = []
        
        for baseline_result in baseline_results:
            if self.baseline_session.is_special_label(baseline_result):
                # Special Label인 경우 intensity 검증 수행
                validated_result = self.intensity_session.validate(baseline_result)
                intensity_validated_results.append(validated_result)
            else:
                # Normal Label인 경우 그대로 사용
                intensity_validated_results.append(baseline_result)
        
        # 4. 세 번째 세션: Final Score Calculation Session (모든 결과에 대해)
        final_results = []
        for idx, validated_result in enumerate(intensity_validated_results):
            # 원본 텍스트 가져오기
            original_text = customer_sentences[idx] if idx < len(customer_sentences) else validated_result.text
            
            # 최종 점수 계산
            final_scores = self.final_score_session.calculate_final_scores(
                classification_result=validated_result,
                text=original_text
            )
            
            # 최종 점수를 ClassificationResult에 적용
            final_result = self.final_score_session.apply_final_scores_to_result(
                classification_result=validated_result,
                final_scores=final_scores
            )
            
            final_results.append(final_result)
        
        return PipelineResult(
            session_id=session_id,
            results=final_results,
            timestamp=datetime.now()
        )
    
    def _process_legacy(self, text: str, session_id: str) -> PipelineResult:
        """
        기존 방식으로 처리 (하위 호환성)
        
        Args:
            text: STT 결과 텍스트 (전체 대화)
            session_id: 세션 ID
        
        Returns:
            PipelineResult (전체 처리 결과)
        """
        # 1. 화자별 문장 분할 (고객/상담원 구분)
        customer_sentences, agent_sentences = self.text_splitter.split_by_speaker(text)
        
        # 2. 각 고객 문장 처리
        results = []
        for sentence in customer_sentences:
            # 1차: 욕설 필터링
            profanity_result = self.profanity_detector.detect(sentence)
            
            # 2차: 발화 의도 분류
            # HEAD: 기본 파라미터
            # logic: 추가 파라미터 지원
            profanity_detected = profanity_result.is_profanity if profanity_result else False
            profanity_category = profanity_result.category if profanity_result else None
            profanity_confidence = profanity_result.confidence if profanity_result else 0.0
            
            classification_result = self.intent_predictor.predict(
                sentence,
                profanity_detected,
                self.session_manager.get_context(session_id),
                profanity_category=profanity_category,  # logic: 추가
                profanity_confidence=profanity_confidence  # logic: 추가
            )
            
            results.append(classification_result)
            
            # 세션 맥락 업데이트
            self.session_manager.add_sentence(session_id, sentence)
        
        return PipelineResult(
            session_id=session_id,
            results=results,
            timestamp=datetime.now()
        )
    
    def process_single_sentence(self, sentence: str, session_id: str) -> ClassificationResult:
        """
        단일 문장 처리 (재설계: 두 단계 세션 구조)
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
        
        Returns:
            ClassificationResult
        """
        # 두 단계 세션 구조 사용
        if self.use_two_stage_session:
            # 1차: 욕설 필터링
            profanity_result = self.profanity_detector.detect(sentence)
            
            profanity_detected = profanity_result.is_profanity if profanity_result else False
            profanity_category = profanity_result.category if profanity_result else None
            profanity_confidence = profanity_result.confidence if profanity_result else 0.0
            
            # 첫 번째 세션: Baseline keyword 검증 + AI hub 모델 검증
            classification_result = self.baseline_session.validate(
                text=sentence,
                session_context=self.session_manager.get_context(session_id),
                profanity_detected=profanity_detected,
                profanity_category=profanity_category,
                profanity_confidence=profanity_confidence
            )
            
            # Special Label인 경우 두 번째 세션으로 전달
            if self.baseline_session.is_special_label(classification_result):
                classification_result = self.intensity_session.validate(classification_result)
            
            # 세 번째 세션: 최종 점수 계산
            final_scores = self.final_score_session.calculate_final_scores(
                classification_result=classification_result,
                text=sentence
            )
            
            # 최종 점수를 ClassificationResult에 적용
            classification_result = self.final_score_session.apply_final_scores_to_result(
                classification_result=classification_result,
                final_scores=final_scores
            )
            
            # 세션 맥락 업데이트
            self.session_manager.add_sentence(session_id, sentence)
            
            return classification_result
        else:
            # 하위 호환성: 기존 방식
            # HEAD: 기본 로직
            # 1차: 욕설 필터링
            profanity_result = self.profanity_detector.detect(sentence)
            
            # 2차: 발화 의도 분류
            classification_result = self.intent_predictor.predict(
                sentence,
                profanity_result.is_profanity if profanity_result else False,
                self.session_manager.get_context(session_id),
                profanity_category=profanity_result.category if profanity_result else None,  # logic: 추가
                profanity_confidence=profanity_result.confidence if profanity_result else 0.0  # logic: 추가
            )
            
            # 세션 맥락 업데이트
            self.session_manager.add_sentence(session_id, sentence)
            
            return classification_result
    
    def process_with_routing(
        self,
        sentence: str,
        session_id: str = "default",
        agent_text: Optional[str] = None
    ) -> RouterResult:
        """
        단일 문장 처리 및 라우팅 (logic: 추가 메서드)
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
            agent_text: 상담사 응답 텍스트 (Normal Label 평가용)
        
        Returns:
            RouterResult
        """
        if not self.enable_routing or not self.label_router:
            raise ValueError("라우팅 기능이 활성화되지 않았습니다. enable_routing=True로 설정하세요.")
        
        # 1. 분류
        classification = self.process_single_sentence(sentence, session_id)
        
        # 2. 라우팅
        session_context = self.session_manager.get_context(session_id)
        router_result = self.label_router.route(
            classification_result=classification,
            session_context=session_context,
            agent_text=agent_text,
            session_id=session_id
        )
        
        return router_result
