"""
Label 라우터

ClassificationResult의 label_type에 따라 적절한 처리 경로로 라우팅
"""
from typing import Optional, List
from datetime import datetime
from logic_classify_system.data.data_structures import (
    ClassificationResult,
    RouterResult,
    EvaluationResult,
    FilteringResult
)
from logic_classify_system.config.labels import LabelType
from logic_classify_system.evaluation.normal_label_evaluator import NormalLabelEvaluator
from logic_classify_system.filtering.special_label_filter import SpecialLabelFilter
import logging

logger = logging.getLogger(__name__)


class LabelRouter:
    """Label 라우터"""
    
    def __init__(
        self,
        normal_label_evaluator: Optional[NormalLabelEvaluator] = None,
        special_label_filter: Optional[SpecialLabelFilter] = None
    ):
        """
        초기화
        
        Args:
            normal_label_evaluator: NormalLabelEvaluator 인스턴스
            special_label_filter: SpecialLabelFilter 인스턴스
        """
        self.normal_label_evaluator = normal_label_evaluator or NormalLabelEvaluator()
        self.special_label_filter = special_label_filter
    
    def route(
        self,
        classification_result: ClassificationResult,
        session_context: Optional[List[str]] = None,
        agent_text: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> RouterResult:
        """
        라우팅 (label_type에 따라 적절한 처리 경로로 라우팅)
        
        Args:
            classification_result: 분류 결과
            session_context: 세션 맥락
            agent_text: 상담사 응답 텍스트 (Normal Label 평가용)
            session_id: 세션 ID (필터링용)
        
        Returns:
            RouterResult
        """
        label_type = classification_result.label_type
        
        if label_type == LabelType.NORMAL.value:
            # Normal Label → Evaluation
            return self._route_to_evaluation(classification_result, agent_text)
        
        elif label_type == LabelType.SPECIAL.value:
            # Special Label → Filtering
            return self._route_to_filtering(classification_result, session_id)
        
        else:
            # UNKNOWN → 에러 처리
            return self._route_to_unknown(classification_result)
    
    def _route_to_evaluation(
        self,
        classification_result: ClassificationResult,
        agent_text: Optional[str] = None
    ) -> RouterResult:
        """Normal Label → Evaluation 라우팅"""
        try:
            evaluation_result = self.normal_label_evaluator.evaluate(
                classification_result,
                agent_text
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
        session_id: Optional[str] = None
    ) -> RouterResult:
        """Special Label → Filtering 라우팅"""
        if not self.special_label_filter:
            logger.warning("SpecialLabelFilter가 없어 필터링을 수행할 수 없습니다.")
            return self._route_to_unknown(classification_result)
        
        try:
            # SpecialLabelDetectionResult 생성
            from logic_classify_system.data.data_structures import SpecialLabelDetectionResult
            
            detection_result = SpecialLabelDetectionResult(
                label=classification_result.label,
                confidence=classification_result.confidence,
                severity="MEDIUM",  # 기본값
                detection_method="routed",
                text=classification_result.text,
                timestamp=classification_result.timestamp or datetime.now()
            )
            
            # 필터링 수행
            filtering_result = self.special_label_filter.filter(
                detection_result,
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
        """UNKNOWN → 에러 처리"""
        logger.warning(f"알 수 없는 label_type: {classification_result.label_type}")
        
        return RouterResult(
            route_type="UNKNOWN",
            result=None,
            classification_result=classification_result
        )

