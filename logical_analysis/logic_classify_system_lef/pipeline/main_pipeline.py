"""
메인 파이프라인 오케스트레이터

전체 파이프라인을 조율하여 문장 단위로 처리
"""

from typing import List, Optional
from datetime import datetime

from ..preprocessing.text_splitter import TextSplitter
from ..profanity_filter.profanity_detector import ProfanityDetector
from ..intent_classifier.intent_predictor import IntentPredictor
from ..data.data_structures import PipelineResult, ClassificationResult
from ..data.session_manager import SessionManager


class MainPipeline:
    """메인 파이프라인"""
    
    def __init__(self):
        """
        메인 파이프라인 초기화
        """
        self.text_splitter = TextSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=False)
        self.intent_predictor = IntentPredictor()
        self.session_manager = SessionManager()
    
    def process(self, text: str, session_id: str) -> PipelineResult:
        """
        전체 파이프라인 실행
        
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
            classification_result = self.intent_predictor.predict(
                sentence,
                profanity_result.is_profanity,
                self.session_manager.get_context(session_id)
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
        단일 문장 처리
        
        Args:
            sentence: 분석할 문장
            session_id: 세션 ID
        
        Returns:
            ClassificationResult
        """
        # 1차: 욕설 필터링
        profanity_result = self.profanity_detector.detect(sentence)
        
        # 2차: 발화 의도 분류
        classification_result = self.intent_predictor.predict(
            sentence,
            profanity_result.is_profanity,
            self.session_manager.get_context(session_id)
        )
        
        # 세션 맥락 업데이트
        self.session_manager.add_sentence(session_id, sentence)
        
        return classification_result

