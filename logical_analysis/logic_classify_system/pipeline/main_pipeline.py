"""
Turn 단위 분석 메인 파이프라인

Turn 단위로 발화를 분석하여 특징점을 추출하고 스코어링
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ..preprocessing.text_splitter import TurnSplitter, Turn
from ..profanity_filter.profanity_detector import ProfanityDetector
from ..intent_classifier.intent_predictor import IntentPredictor
from ..feature_extractor.customer_feature_extractor import CustomerFeatureExtractor
from ..feature_extractor.agent_feature_extractor import AgentFeatureExtractor
from ..data.data_structures import (
    PipelineResult,
    TurnAnalysisResult,
    CustomerAnalysisResult,
    AgentAnalysisResult,
    ProfanityResult,
    ClassificationResult
)


class MainPipeline:
    """Turn 단위 분석 메인 파이프라인"""
    
    def __init__(self):
        """
        파이프라인 초기화
        """
        self.turn_splitter = TurnSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=False)
        self.intent_predictor = IntentPredictor()
        self.customer_feature_extractor = CustomerFeatureExtractor()
        self.agent_feature_extractor = AgentFeatureExtractor()
    
    def process(self, stt_data: Dict[str, Any]) -> PipelineResult:
        """
        STT 결과를 Turn 단위로 처리
        
        Args:
            stt_data: STT 결과 딕셔너리
                예: {
                    "session_id": "session_001",
                    "segments": [
                        {"speaker": "customer", "text": "안녕하세요", "timestamp": ...},
                        {"speaker": "agent", "text": "네 안녕하세요", "timestamp": ...},
                        ...
                    ]
                }
        
        Returns:
            PipelineResult (Turn 단위 분석 결과 리스트)
        """
        session_id = stt_data.get("session_id", "unknown")
        
        # 1. Turn 단위로 분할
        turns = self.turn_splitter.split_into_turns(stt_data)
        total_turns = len(turns)
        
        # 2. 각 Turn 처리
        turn_results = []
        for idx, turn in enumerate(turns):
            # 세션 시작/끝 여부 결정
            is_start = (idx == 0)
            is_end = (idx == total_turns - 1)
            
            turn_result = self.process_turn(turn, session_id, is_start=is_start, is_end=is_end)
            turn_results.append(turn_result)
        
        return PipelineResult(
            session_id=session_id,
            turn_results=turn_results,
            timestamp=datetime.now()
        )
    
    def process_turn(
        self,
        turn: Turn,
        session_id: str,
        is_start: bool = False,
        is_end: bool = False
    ) -> TurnAnalysisResult:
        """
        단일 Turn 처리
        
        Args:
            turn: Turn 객체
            session_id: 세션 ID
            is_start: 세션 시작 여부 (인사 검사용)
            is_end: 세션 종료 여부 (마무리 검사용)
        
        Returns:
            TurnAnalysisResult
        """
        timestamp = datetime.now()
        
        # 1. 손님 발화 분석
        customer_result = self._analyze_customer_turn(
            turn.customer_text,
            session_id,
            turn.turn_index,
            timestamp
        )
        
        # 2. 상담원 발화 분석 (있는 경우)
        agent_result = None
        if turn.agent_text:
            agent_result = self._analyze_agent_turn(
                turn.agent_text,
                customer_result.classification_result.label,
                session_id,
                turn.turn_index,
                timestamp,
                is_start=is_start,
                is_end=is_end
            )
        
        # 3. Turn 단위 종합 점수 계산
        turn_scores = self._calculate_turn_scores(customer_result, agent_result)
        
        return TurnAnalysisResult(
            session_id=session_id,
            turn_index=turn.turn_index,
            customer_result=customer_result,
            agent_result=agent_result,
            turn_scores=turn_scores
        )
    
    def _analyze_customer_turn(
        self,
        text: str,
        session_id: str,
        turn_index: int,
        timestamp: datetime
    ) -> CustomerAnalysisResult:
        """손님 발화 Turn 분석"""
        # 1. 욕설 필터링
        profanity_result = self.profanity_detector.detect(text)
        
        # 2. 발화 의도 분류 (Turn 단위이므로 session_context 최소 사용)
        # profanity_result 정보를 IntentPredictor에 전달하여 통합 처리
        classification_result = self.intent_predictor.predict(
            text,
            profanity_result.is_profanity,
            profanity_confidence=profanity_result.confidence if profanity_result.is_profanity else 0.0,
            session_context=None  # Turn 단위 분석이므로 세션 맥락 미사용
        )
        
        # 3. 특징점 추출
        feature_scores, extracted_features = self.customer_feature_extractor.extract_features(
            text,
            profanity_result,
            classification_result
        )
        
        return CustomerAnalysisResult(
            session_id=session_id,
            turn_index=turn_index,
            text=text,
            timestamp=timestamp,
            profanity_result=profanity_result,
            classification_result=classification_result,
            feature_scores=feature_scores,
            extracted_features=extracted_features
        )
    
    def _analyze_agent_turn(
        self,
        text: str,
        customer_label: str,
        session_id: str,
        turn_index: int,
        timestamp: datetime,
        is_start: bool = False,
        is_end: bool = False
    ) -> AgentAnalysisResult:
        """
        상담원 발화 Turn 분석 (Keyword 기반 매뉴얼 준수 평가)
        
        Args:
            text: 상담원 발화 텍스트
            customer_label: 해당 손님 발화의 Label (CAR)
            session_id: 세션 ID
            turn_index: Turn 인덱스
            timestamp: 타임스탬프
            is_start: 세션 시작 여부 (인사 검사용)
            is_end: 세션 종료 여부 (마무리 검사용)
        
        Returns:
            AgentAnalysisResult
        """
        
        # 감정 라벨 추출 (현재는 미구현, 향후 감정 분류 시스템 연동 필요)
        # TODO: 감정 분류 시스템에서 customer_text 기반으로 감정 라벨 추출
        emotion_label = None  # 기본값: "NEUTRAL" (ManualComplianceChecker 내부에서 처리)
        
        # 특징점 추출 (Keyword 기반 매뉴얼 준수 평가)
        # - 감정 라벨 + CAR 조합에 따른 매뉴얼 키워드 적용
        # - 작은 조각 단위(키워드/구)로 포함 여부 확인
        feature_scores, compliance_details, extracted_features = self.agent_feature_extractor.extract_features(
            text=text,
            customer_label=customer_label,
            emotion_label=emotion_label,  # None일 경우 내부에서 "NEUTRAL" 사용
            is_start=is_start,
            is_end=is_end
        )
        
        # 매뉴얼 준수도 점수 추출
        manual_compliance_score = feature_scores.get("manual_compliance_score", 0.0)
        
        return AgentAnalysisResult(
            session_id=session_id,
            turn_index=turn_index,
            text=text,
            timestamp=timestamp,
            corresponding_customer_label=customer_label,
            emotion_label=emotion_label,  # 추출된 감정 라벨 저장
            manual_compliance_score=manual_compliance_score,
            compliance_details=compliance_details,
            feature_scores=feature_scores,
            extracted_features=extracted_features
        )
    
    def _calculate_turn_scores(
        self,
        customer_result: CustomerAnalysisResult,
        agent_result: Optional[AgentAnalysisResult]
    ) -> Dict[str, float]:
        """
        Turn 단위 종합 점수 계산
        
        주의: 해당 Turn에 대한 평가만 포함 (세션 전체 평가는 후속 모듈에서 수행)
        """
        turn_scores = {}
        
        # 1. 손님 문제 발생 가능성 점수
        # Special Label 또는 높은 리스크 특징점 기반
        problem_scores = [
            customer_result.feature_scores.get("profanity_score", 0.0),
            customer_result.feature_scores.get("threat_score", 0.0),
            customer_result.feature_scores.get("sexual_harassment_score", 0.0),
            customer_result.feature_scores.get("hate_speech_score", 0.0),
            customer_result.feature_scores.get("unreasonable_demand_score", 0.0),
            customer_result.feature_scores.get("repetition_keyword_score", 0.0)  # 반복 표현 점수 추가
        ]
        turn_scores["customer_problem_score"] = max(problem_scores)
        
        # 2. 상담원 대응 품질 점수 (상담원 발화가 있는 경우)
        if agent_result:
            quality_scores = [
                agent_result.feature_scores.get("manual_compliance_score", 0.0),
                agent_result.feature_scores.get("information_accuracy_score", 0.0),
                agent_result.feature_scores.get("communication_clarity_score", 0.0),
                agent_result.feature_scores.get("empathy_score", 0.0),
                agent_result.feature_scores.get("problem_solving_score", 0.0)
            ]
            # 가중 평균 계산
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            turn_scores["agent_response_quality_score"] = sum(
                score * weight for score, weight in zip(quality_scores, weights)
            )
        else:
            turn_scores["agent_response_quality_score"] = 0.0
        
        # 3. Turn 리스크 점수
        # 손님 문제 점수와 상담원 대응 품질을 종합
        if agent_result:
            # 상담원이 잘 대응하면 리스크 감소
            risk_adjustment = (1.0 - turn_scores["agent_response_quality_score"]) * 0.3
            turn_scores["turn_risk_score"] = min(
                turn_scores["customer_problem_score"] + risk_adjustment,
                1.0
            )
        else:
            # 상담원 대응이 없으면 손님 문제 점수 그대로
            turn_scores["turn_risk_score"] = turn_scores["customer_problem_score"]
        
        return turn_scores

