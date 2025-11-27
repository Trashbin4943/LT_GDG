"""
Label 기반 라우팅

Normal Label과 특수 Label에 따라 적절한 처리 경로로 라우팅 (HEAD 기반)
ClassificationResult의 label_type에 따라 적절한 처리 경로로 라우팅 (logic 기능 통합)
"""

from typing import Optional, List
from datetime import datetime
import logging

from ..data.data_structures import (
    ClassificationResult,
    RouterResult,
    EvaluationResult,
    FilteringResult,
    SpecialLabelDetectionResult
)
from ..config.labels import LabelType
from ..evaluation.normal_label_evaluator import NormalLabelEvaluator
from ..filtering.special_label_filter import SpecialLabelFilter

logger = logging.getLogger(__name__)


class LabelRouter:
    """Label 라우터 (HEAD 기반 + logic 기능 통합)"""
    
    def __init__(
        self,
        normal_label_evaluator: Optional[NormalLabelEvaluator] = None,
        special_label_filter: Optional[SpecialLabelFilter] = None
    ):
        """
        Label 라우터 초기화
        
        Args:
            normal_label_evaluator: NormalLabelEvaluator 인스턴스 (logic: 추가)
            special_label_filter: SpecialLabelFilter 인스턴스 (logic: 추가)
        """
        # HEAD: 기본 구조 유지
        self.evaluator = normal_label_evaluator or NormalLabelEvaluator()
        self.filter = special_label_filter or SpecialLabelFilter()
        
        # logic: 별도 변수명 유지 (호환성)
        self.normal_label_evaluator = self.evaluator
        self.special_label_filter = self.filter
    
    def route(
        self,
        classification_result: ClassificationResult,
        session_context: Optional[List[str]] = None,
        agent_text: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> RouterResult:
        """
        Label 기반 라우팅 (HEAD 시그니처 유지 + logic 호환성)
        
        Args:
            classification_result: 분류 결과
            session_context: 세션 맥락
            agent_text: 상담사 발화 (Normal Label 평가용)
            session_id: 세션 ID (필터링용) (logic: 추가)
        
        Returns:
            RouterResult
        """
        label_type = classification_result.label_type
        
        # logic: LabelType Enum 사용
        if label_type == LabelType.NORMAL.value or label_type == "NORMAL":
            # Normal Label → Evaluation
            return self._route_to_evaluation(classification_result, agent_text, session_context)
        
        elif label_type == LabelType.SPECIAL.value or label_type == "SPECIAL":
            # Special Label → Filtering
            return self._route_to_filtering(classification_result, session_context, session_id)
        
        else:
            # UNKNOWN → 에러 처리
            return self._route_to_unknown(classification_result)
    
    def _route_to_evaluation(
        self,
        classification_result: ClassificationResult,
        agent_text: Optional[str] = None,
        session_context: Optional[List[str]] = None
    ) -> RouterResult:
        """Normal Label → Evaluation 라우팅 (HEAD + logic 통합)"""
        try:
            # HEAD 방식: 기존 파라미터 사용
            if agent_text is None:
                agent_text = ""
            
            # HEAD: 기존 evaluate 메서드 호출
            evaluation_result = self.evaluator.evaluate(
                label=classification_result.label,
                customer_text=classification_result.text,
                agent_text=agent_text,
                session_context=session_context or [],
                classification_result=classification_result  # logic 방식도 지원
            )
            
            return RouterResult(
                route_type="EVALUATION",
                result=evaluation_result,
                classification_result=classification_result
            )
        except Exception as e:
            logger.error(f"평가 실패: {e}")
            return self._route_to_unknown(classification_result)
    
    def _route_to_filtering(
        self,
        classification_result: ClassificationResult,
        session_context: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> RouterResult:
        """Special Label → Filtering 라우팅 (HEAD + logic 통합)"""
        try:
            # HEAD 방식: 기존 filter 메서드 호출
            filtering_result = self.filter.filter(
                label=classification_result.label,
                text=classification_result.text,
                session_context=session_context,
                session_id=session_id  # logic 방식도 지원
            )
            
            # logic 방식: detection_result 사용
            if not filtering_result:
                # SpecialLabelDetectionResult 생성
                detection_result = SpecialLabelDetectionResult(
                    label=classification_result.label,
                    confidence=classification_result.confidence,
                    severity="MEDIUM",  # 기본값
                    detection_method="routed",
                    text=classification_result.text,
                    timestamp=classification_result.timestamp or datetime.now()
                )
                
                filtering_result = self.filter.filter(
                    detection_result=detection_result,
                    session_id=session_id
                )
            
            return RouterResult(
                route_type="FILTERING",
                result=filtering_result,
                classification_result=classification_result
            )
        except Exception as e:
            logger.error(f"필터링 실패: {e}")
            return self._route_to_unknown(classification_result)
    
    def _route_to_unknown(
        self,
        classification_result: ClassificationResult
    ) -> RouterResult:
        """UNKNOWN → 에러 처리 (logic: 추가)"""
        logger.warning(f"알 수 없는 label_type: {classification_result.label_type}")
        
        return RouterResult(
            route_type="UNKNOWN",
            result=None,
            classification_result=classification_result
        )
