"""
메인 파이프라인 오케스트레이터

전체 파이프라인을 조율하여 문장 단위로 처리 (HEAD 기반)
전체 프로세스 조율, 세션 관리, 파이프라인 모드 제어 (logic 기능 통합)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..preprocessing.text_splitter import TextSplitter
from ..profanity_filter.profanity_detector import ProfanityDetector
from ..intent_classifier.intent_predictor import IntentPredictor
from ..intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor

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
from ..config.labels import PipelineMode

# logic: 선택적 import
try:
    from ..labeling.label_router import LabelRouter
except ImportError:
    LabelRouter = None

logger = logging.getLogger(__name__)


class MainPipeline:
    """메인 파이프라인 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(
        self,
        intensity_model_path: Optional[str] = None,
        ternary_model_path: Optional[str] = None,
        use_enhanced_predictor: bool = True,
        mode: Optional[PipelineMode] = None,
        use_korcen: bool = False,
        enable_routing: bool = False  # logic: 라우팅 기능 활성화 여부
    ):
        """
        파이프라인 초기화
        
        Args:
            intensity_model_path: Intensity Regression 모델 경로 (HEAD)
            ternary_model_path: 3진 분류 모델 경로 (HEAD)
            use_enhanced_predictor: 향상된 예측기 사용 여부 (기본: True) (HEAD)
            mode: 파이프라인 모드 (logic: 추가)
            use_korcen: Korcen 사용 여부 (logic: 추가)
            enable_routing: 라우팅 기능 활성화 여부 (logic: 추가)
        """
        self.text_splitter = TextSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=use_korcen)
        
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
        전체 파이프라인 실행 (HEAD 시그니처 유지)
        
        Args:
            text: STT 결과 텍스트 (전체 대화)
            session_id: 세션 ID
        
        Returns:
            PipelineResult (전체 처리 결과)
        """
        # 1. 문장 단위 분할
        sentences = self.text_splitter.split_sentences(text)
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
        단일 문장 처리 (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
        
        Returns:
            ClassificationResult
        """
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
