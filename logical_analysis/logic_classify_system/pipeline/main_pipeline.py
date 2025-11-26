"""
메인 파이프라인 오케스트레이터

전체 파이프라인을 조율하여 문장 단위로 처리
"""

from typing import List, Optional
from datetime import datetime

from ..preprocessing.text_splitter import TextSplitter
from ..profanity_filter.profanity_detector import ProfanityDetector
from ..intent_classifier.intent_predictor import IntentPredictor
<<<<<<< Updated upstream
from ..data.data_structures import PipelineResult, ClassificationResult
from ..data.session_manager import SessionManager
=======
from ..intent_classifier.enhanced_intent_predictor import EnhancedIntentPredictor
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
>>>>>>> Stashed changes


class MainPipeline:
    """메인 파이프라인"""
    
    def __init__(
        self,
        intensity_model_path: Optional[str] = None,
        ternary_model_path: Optional[str] = None,
        use_enhanced_predictor: bool = True
    ):
        """
<<<<<<< Updated upstream
        메인 파이프라인 초기화
=======
        파이프라인 초기화
        
        Args:
            intensity_model_path: Intensity Regression 모델 경로
            ternary_model_path: 3진 분류 모델 경로
            use_enhanced_predictor: 향상된 예측기 사용 여부 (기본: True)
>>>>>>> Stashed changes
        """
        self.text_splitter = TextSplitter()
        self.profanity_detector = ProfanityDetector(use_korcen=False)
<<<<<<< Updated upstream
        self.intent_predictor = IntentPredictor()
        self.session_manager = SessionManager()
=======
        
        # [NEW] 향상된 의도 예측기 사용 (이중 모델 통합)
        if use_enhanced_predictor and (intensity_model_path or ternary_model_path):
            self.intent_predictor = EnhancedIntentPredictor(
                intensity_model_path=intensity_model_path,
                ternary_model_path=ternary_model_path,
                use_models=True
            )
        else:
            # 기존 예측기 사용 (하위 호환성)
            self.intent_predictor = IntentPredictor()
        
        self.customer_feature_extractor = CustomerFeatureExtractor()
        self.agent_feature_extractor = AgentFeatureExtractor()
>>>>>>> Stashed changes
    
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
        
<<<<<<< Updated upstream
        # 2차: 발화 의도 분류
=======
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
        
        # 3. Turn 단위 종합 점수 계산 (Intensity 정보 활용)
        intensity_info = None
        if hasattr(customer_result.classification_result, 'intensity'):
            intensity_info = {
                'intensity': customer_result.classification_result.intensity or 0.0,
                'intensity_level': customer_result.classification_result.intensity_level or 'LOW',
                'is_immoral': customer_result.classification_result.is_immoral or False,
                'immorality_confidence': customer_result.classification_result.immorality_confidence or 0.0
            }
        
        turn_scores = self._calculate_turn_scores(
            customer_result,
            agent_result,
            intensity_info=intensity_info
        )
        
        return TurnAnalysisResult(
            session_id=session_id,
            turn_index=turn.turn_index,
            customer_result=customer_result,
            # agent_result=agent_result,
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
>>>>>>> Stashed changes
        classification_result = self.intent_predictor.predict(
            sentence,
            profanity_result.is_profanity,
            self.session_manager.get_context(session_id)
        )
        
        # 세션 맥락 업데이트
        self.session_manager.add_sentence(session_id, sentence)
        
<<<<<<< Updated upstream
        return classification_result
=======
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
        agent_result: Optional[AgentAnalysisResult],
        intensity_info: Optional[Dict[str, any]] = None
    ) -> Dict[str, float]:
        """
        Turn 단위 종합 점수 계산 (Intensity 정보 활용)
        
        주의: 해당 Turn에 대한 평가만 포함 (세션 전체 평가는 후속 모듈에서 수행)
        
        현재 구현:
        - customer_problem_score: 고객 문제 발생 가능성 점수
        - agent_response_quality_score: 상담원 대응 품질 점수 (가중 평균)
        - turn_risk_score: customer_problem_score - 상담원 품질 조정 + intensity 기반 조정
        
        Args:
            customer_result: 고객 분석 결과
            agent_result: 상담원 분석 결과
            intensity_info: Intensity 정보 (intensity, intensity_level 등)
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
        
        # [NEW] Intensity 정보 반영
        if intensity_info:
            intensity = intensity_info.get('intensity', 0.0)
            intensity_level = intensity_info.get('intensity_level', 'LOW')
            
            # Intensity 기반 점수 조정
            # intensity 범위: 0.0 ~ 3.0 (윤리검증 데이터셋 기반)
            if intensity_level == 'HIGH':
                # HIGH 단계: 모든 점수에 가중치 적용
                problem_scores = [score * 1.2 for score in problem_scores]
                problem_scores.append(min(intensity / 3.0, 1.0))  # intensity 직접 반영
            elif intensity_level == 'MEDIUM':
                # MEDIUM 단계: 중간 가중치
                problem_scores = [score * 1.1 for score in problem_scores]
                problem_scores.append(min(intensity / 3.0, 1.0) * 0.8)
            else:
                # LOW 단계: intensity만 추가
                problem_scores.append(min(intensity / 3.0, 1.0) * 0.5)
        
        turn_scores["customer_problem_score"] = min(max(problem_scores), 1.0)
        
        # 2. 상담원 대응 품질 점수 계산
        if agent_result and agent_result.feature_scores:
            quality_scores = [
                agent_result.feature_scores.get("manual_compliance_score", 0.0),
                agent_result.feature_scores.get("information_accuracy_score", 0.0),
                agent_result.feature_scores.get("communication_clarity_score", 0.0),
                agent_result.feature_scores.get("empathy_score", 0.0),
                agent_result.feature_scores.get("problem_solving_score", 0.0)
            ]
            # 가중치: 매뉴얼 준수도(30%), 정보 정확성(25%), 소통 명확성(20%), 공감 표현(15%), 문제 해결(10%)
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            turn_scores["agent_response_quality_score"] = sum(
                score * weight for score, weight in zip(quality_scores, weights)
            )
        else:
            turn_scores["agent_response_quality_score"] = 0.0
        
        # 3. Turn 리스크 점수 계산
        # 기본 리스크: customer_problem_score
        base_risk = turn_scores["customer_problem_score"]
        
        # [NEW] Phase 5: 상담원 대응 품질에 따른 리스크 조정
        # 상담원이 잘 대응하면 리스크 감소
        if agent_result and turn_scores["agent_response_quality_score"] > 0.0:
            # agent_response_quality_score가 높을수록 (1.0에 가까울수록) 리스크 감소
            # 최대 30% 감소 가능 (quality_score=1.0일 때)
            quality_adjustment = turn_scores["agent_response_quality_score"] * 0.3
            adjusted_risk = max(0.0, base_risk - quality_adjustment)
        else:
            # 상담원 대응이 없거나 품질 점수가 0이면 기본 리스크 사용
            adjusted_risk = base_risk
        
        # [NEW] Intensity level에 따른 최종 조정
        # 상담원 평가 조정 후 Intensity level 반영
        if intensity_info:
            intensity_level = intensity_info.get('intensity_level', 'LOW')
            if intensity_level == 'HIGH':
                # HIGH: 리스크 증가 (15%)
                turn_scores["turn_risk_score"] = min(adjusted_risk * 1.15, 1.0)
            elif intensity_level == 'MEDIUM':
                # MEDIUM: 약간 증가 (5%)
                turn_scores["turn_risk_score"] = min(adjusted_risk * 1.05, 1.0)
            else:
                # LOW: 그대로
                turn_scores["turn_risk_score"] = min(adjusted_risk, 1.0)
        else:
            turn_scores["turn_risk_score"] = min(adjusted_risk, 1.0)
        
        return turn_scores
>>>>>>> Stashed changes

