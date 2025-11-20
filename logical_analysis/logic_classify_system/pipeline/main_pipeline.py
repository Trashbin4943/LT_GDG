"""
메인 파이프라인 오케스트레이터

전체 프로세스 조율, 세션 관리, 파이프라인 모드 제어
"""
from typing import Optional, List
from datetime import datetime
from logic_classify_system.data.data_structures import (
    PipelineResult,
    ClassificationResult,
    RouterResult
)
from logic_classify_system.config.labels import PipelineMode
from logic_classify_system.preprocessing.text_splitter import TextSplitter
from logic_classify_system.profanity_filter.profanity_detector import ProfanityDetector
from logic_classify_system.intent_classifier.intent_predictor import IntentPredictor
from logic_classify_system.labeling.label_router import LabelRouter
from logic_classify_system.data.session_manager import SessionManager
from logic_classify_system.models.aihub_ethic_model import AIHubEthicModel
from logic_classify_system.filtering.aihub_special_label_detector import AIHubSpecialLabelDetector
from logic_classify_system.filtering.special_label_filter import SpecialLabelFilter
from logic_classify_system.config.model_config import ModelConfig
import logging

logger = logging.getLogger(__name__)


class MainPipeline:
    """메인 파이프라인 오케스트레이터"""
    
    def __init__(
        self,
        mode: PipelineMode = PipelineMode.default(),
        use_korcen: bool = True,
        aihub_base_model_path: Optional[str] = None,
        aihub_model1_checkpoint: Optional[str] = None,
        aihub_model2_checkpoint: Optional[str] = None,
        aihub_device: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            mode: 파이프라인 모드
            use_korcen: Korcen 사용 여부
            aihub_base_model_path: AI-Hub 기본 모델 경로
            aihub_model1_checkpoint: 모델 1 체크포인트 경로
            aihub_model2_checkpoint: 모델 2 체크포인트 경로
            aihub_device: 사용할 디바이스
        """
        self.mode = mode
        self.use_korcen = use_korcen
        
        # 모듈 초기화
        self.text_splitter = TextSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=use_korcen)
        self.session_manager = SessionManager()
        
        # AI-Hub 모델 초기화 (선택사항)
        self.aihub_model = None
        self.aihub_detector = None
        self.special_label_filter = None
        
        if aihub_base_model_path or aihub_model1_checkpoint or aihub_model2_checkpoint:
            try:
                model_paths = ModelConfig.get_model_paths(
                    base_model_path=aihub_base_model_path,
                    model1_checkpoint=aihub_model1_checkpoint,
                    model2_checkpoint=aihub_model2_checkpoint
                )
                
                self.aihub_model = AIHubEthicModel(
                    base_model_path=model_paths["base_model_path"],
                    model1_checkpoint=model_paths["model1_checkpoint"],
                    model2_checkpoint=model_paths["model2_checkpoint"],
                    device=aihub_device
                )
                
                self.aihub_detector = AIHubSpecialLabelDetector(aihub_model=self.aihub_model)
                self.special_label_filter = SpecialLabelFilter(aihub_detector=self.aihub_detector)
                
                logger.info("AI-Hub 모델 로드 완료")
            except Exception as e:
                logger.warning(f"AI-Hub 모델 로드 실패 (Baseline 규칙만 사용): {e}")
        
        # IntentPredictor 초기화
        self.intent_predictor = IntentPredictor(
            mode=mode,
            special_label_filter=self.special_label_filter
        )
        
        # LabelRouter 초기화
        self.label_router = LabelRouter(
            special_label_filter=self.special_label_filter
        )
    
    def process(
        self,
        text: str,
        session_id: str = "default"
    ) -> PipelineResult:
        """
        전체 텍스트 처리 (STT 결과 텍스트)
        
        Args:
            text: STT 결과 텍스트 (여러 발화 포함 가능)
            session_id: 세션 ID
        
        Returns:
            PipelineResult
        """
        # 1. 텍스트 분할 및 화자 구분
        customer_sentences, agent_sentences = self.text_splitter.split_text(text)
        
        if not customer_sentences:
            return PipelineResult(
                results=[],
                session_id=session_id,
                timestamp=datetime.now()
            )
        
        # 2. 각 고객 발화 처리
        results = []
        for sentence in customer_sentences:
            classification = self.process_single_sentence(sentence, session_id)
            results.append(classification)
        
        return PipelineResult(
            results=results,
            session_id=session_id,
            timestamp=datetime.now()
        )
    
    def process_single_sentence(
        self,
        sentence: str,
        session_id: str = "default"
    ) -> ClassificationResult:
        """
        단일 문장 처리
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
        
        Returns:
            ClassificationResult
        """
        # 1. 세션 맥락 조회
        session_context = self.session_manager.get_session_context(session_id)
        
        # 2. 욕설 감지
        profanity_result = self.profanity_detector.detect(sentence)
        profanity_detected = profanity_result.is_profanity if profanity_result else False
        profanity_category = profanity_result.category if profanity_result else None
        profanity_confidence = profanity_result.confidence if profanity_result else 0.0
        
        # 3. 의도 분류
        classification = self.intent_predictor.predict(
            text=sentence,
            profanity_detected=profanity_detected,
            session_context=session_context,
            profanity_category=profanity_category,
            profanity_confidence=profanity_confidence
        )
        
        # 4. 세션 맥락 업데이트
        self.session_manager.add_to_session(session_id, sentence)
        
        return classification
    
    def process_with_routing(
        self,
        sentence: str,
        session_id: str = "default",
        agent_text: Optional[str] = None
    ) -> RouterResult:
        """
        단일 문장 처리 및 라우팅
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
            agent_text: 상담사 응답 텍스트 (Normal Label 평가용)
        
        Returns:
            RouterResult
        """
        # 1. 분류
        classification = self.process_single_sentence(sentence, session_id)
        
        # 2. 라우팅
        session_context = self.session_manager.get_session_context(session_id)
        router_result = self.label_router.route(
            classification_result=classification,
            session_context=session_context,
            agent_text=agent_text,
            session_id=session_id
        )
        
        return router_result
