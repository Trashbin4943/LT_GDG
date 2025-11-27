"""
Label 라우터

ClassificationResult의 label_type에 따라 적절한 처리 경로로 라우팅
- Normal Label → Evaluation
- Special Label → Filtering
"""

from typing import List, Optional
import logging

from ..data.data_structures import (
    ClassificationResult,
    RouterResult,
    EvaluationResult,
    FilteringResult
)
from ..evaluation.normal_label_evaluator import NormalLabelEvaluator
from ..filtering.special_label_filter import SpecialLabelFilter

logger = logging.getLogger(__name__)


class LabelRouter:
    """Label 라우터 (Normal/Special Label 분기)"""
    
    def __init__(self):
        """
        LabelRouter 초기화
        
        NormalLabelEvaluator와 SpecialLabelFilter 인스턴스를 생성합니다.
        """
        self.evaluator = NormalLabelEvaluator()
        self.filter = SpecialLabelFilter()
        logger.info("LabelRouter 초기화 완료")
    
    def route(
        self,
        classification_result: ClassificationResult,
        session_context: List[str],
        agent_text: Optional[str] = None,
        session_id: str = "default"
    ) -> RouterResult:
        """
        ClassificationResult를 label_type에 따라 적절한 처리 경로로 라우팅
        
        Args:
            classification_result: 분류 결과
            session_context: 세션 맥락
            agent_text: 상담사 응답 텍스트 (Normal Label 평가용)
            session_id: 세션 ID
        
        Returns:
            RouterResult: 라우팅 결과
        """
        if not classification_result:
            logger.error("classification_result가 None입니다.")
            raise ValueError("classification_result는 필수입니다.")
        
        label_type = classification_result.label_type
        
        logger.debug(
            f"[라우팅] session_id={session_id}, "
            f"label={classification_result.label}, "
            f"label_type={label_type}"
        )
        
        if label_type == "NORMAL":
            # Normal Label → Evaluation
            try:
                evaluation_result = self.evaluator.evaluate(
                    classification_result=classification_result,
                    agent_text=agent_text,
                    session_context=session_context
                )
                
                logger.debug(
                    f"[라우팅 완료] NORMAL → EVALUATION, "
                    f"label={classification_result.label}, "
                    f"score={evaluation_result.score}"
                )
                
                return RouterResult(
                    route_type="EVALUATION",
                    result=evaluation_result,
                    classification_result=classification_result
                )
            except Exception as e:
                logger.error(
                    f"Normal Label 평가 중 오류 발생: {e}, "
                    f"label={classification_result.label}",
                    exc_info=True
                )
                # 평가 실패 시에도 RouterResult 반환 (UNKNOWN 처리)
                return RouterResult(
                    route_type="UNKNOWN",
                    result=None,
                    classification_result=classification_result
                )
        
        elif label_type == "SPECIAL":
            # Special Label → Filtering
            try:
                filtering_result = self.filter.filter(
                    label=classification_result.label,
                    text=classification_result.text,
                    session_context=session_context,
                    session_id=session_id
                )
                
                logger.debug(
                    f"[라우팅 완료] SPECIAL → FILTERING, "
                    f"label={classification_result.label}, "
                    f"severity={filtering_result.severity}, "
                    f"action={filtering_result.action}"
                )
                
                return RouterResult(
                    route_type="FILTERING",
                    result=filtering_result,
                    classification_result=classification_result
                )
            except Exception as e:
                logger.error(
                    f"Special Label 필터링 중 오류 발생: {e}, "
                    f"label={classification_result.label}",
                    exc_info=True
                )
                # 필터링 실패 시에도 RouterResult 반환 (UNKNOWN 처리)
                return RouterResult(
                    route_type="UNKNOWN",
                    result=None,
                    classification_result=classification_result
                )
        
        else:
            # Unknown Label Type
            logger.warning(
                f"알 수 없는 label_type: {label_type}, "
                f"label={classification_result.label}"
            )
            return RouterResult(
                route_type="UNKNOWN",
                result=None,
                classification_result=classification_result
            )

