"""
Baseline Validation Session (첫 번째 세션)

전반부 처리:
1. Baseline keyword 기반으로 is_moral 검증 및 label 부여
2. AI hub 기반 학습 모델로 검증

의존성:
- IntentBaselineRules: Baseline keyword 규칙
- AIHubEthicModel: AI hub 윤리 검증 모델 (선택적)
- ClassificationResult: 결과 데이터 구조
- LabelType: 라벨 타입 정의
"""

from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime
import logging

from ..intent_classifier.baseline_rules import IntentBaselineRules
from ..models.aihub_ethic_model import AIHubEthicModel
from ..data.data_structures import ClassificationResult
from ..config.labels import NORMAL_LABELS, SPECIAL_LABELS, LabelType

logger = logging.getLogger(__name__)


class BaselineValidationSession:
    """
    Baseline Validation Session
    
    전반부 처리 세션:
    - Baseline keyword 기반 검증
    - AI hub 모델 기반 검증
    """
    
    def __init__(
        self,
        aihub_model: Optional[AIHubEthicModel] = None,
        aihub_base_path: Optional[str] = None,
        aihub_model1_checkpoint: Optional[str] = None,
        aihub_model2_checkpoint: Optional[str] = None,
        baseline_rules: Optional[IntentBaselineRules] = None
    ):
        """
        Baseline Validation Session 초기화
        
        Args:
            aihub_model: AI hub 모델 인스턴스 (선택적, 우선순위 1)
            aihub_base_path: AI hub 모델 기본 경로 (aihub_model이 없을 때 사용)
            aihub_model1_checkpoint: AI hub 모델 1 체크포인트 경로
            aihub_model2_checkpoint: AI hub 모델 2 체크포인트 경로
            baseline_rules: IntentBaselineRules 인스턴스 (선택적, 테스트용)
        
        Raises:
            None (에러 발생 시 경고 로그만 출력하고 계속 진행)
        """
        # Baseline 규칙 초기화
        if baseline_rules:
            self.baseline_rules = baseline_rules
        else:
            self.baseline_rules = IntentBaselineRules()
        
        # AI hub 모델 초기화 (우선순위: aihub_model > aihub_base_path > None)
        if aihub_model:
            self.aihub_model = aihub_model
            logger.debug("AI hub 모델 인스턴스를 직접 사용합니다.")
        elif aihub_base_path:
            try:
                self.aihub_model = AIHubEthicModel(
                    base_model_path=aihub_base_path,
                    model1_checkpoint=aihub_model1_checkpoint,
                    model2_checkpoint=aihub_model2_checkpoint
                )
                logger.debug(f"AI hub 모델 로드 완료: {aihub_base_path}")
            except Exception as e:
                logger.warning(f"AI hub 모델 초기화 실패: {e}. Baseline 규칙만 사용합니다.")
                self.aihub_model = None
        else:
            self.aihub_model = None
            logger.debug("AI hub 모델을 사용하지 않습니다. Baseline 규칙만 사용합니다.")
    
    def validate(
        self,
        text: str,
        session_context: Optional[List[str]] = None,
        profanity_detected: bool = False,
        profanity_category: Optional[str] = None,
        profanity_confidence: float = 0.0
    ) -> ClassificationResult:
        """
        Baseline 검증 및 AI hub 모델 검증 수행
        
        처리 순서:
        1. Baseline keyword 기반 검증
        2. AI hub 모델 기반 검증 (모델이 있는 경우)
        3. 최종 Label 결정 (Special 또는 Normal)
        
        Args:
            text: 분석할 텍스트 (필수)
            session_context: 세션 맥락 (선택적, 반복성 감지용)
            profanity_detected: 욕설 감지 여부 (기본: False)
            profanity_category: 욕설 카테고리 (선택적)
            profanity_confidence: 욕설 신뢰도 (0.0 ~ 1.0, 기본: 0.0)
        
        Returns:
            ClassificationResult:
                - label: 분류된 라벨 (PROFANITY, VIOLENCE_THREAT 등 또는 INQUIRY)
                - label_type: "SPECIAL" 또는 "NORMAL"
                - confidence: 신뢰도 (0.0 ~ 1.0)
                - probabilities: 각 라벨별 확률 딕셔너리
                - is_immoral: AI hub 모델 결과 (있는 경우)
                - immorality_confidence: AI hub 모델 신뢰도 (있는 경우)
                - metadata: AI hub 모델 상세 정보 (있는 경우)
        
        Raises:
            None (에러 발생 시 경고 로그만 출력하고 기본값 반환)
        """
        # ==========================================
        # 1단계: Baseline keyword 기반 검증
        # ==========================================
        baseline_results = self.baseline_rules.detect_special_labels(
            text,
            session_context,
            return_type="list"
        )
        
        # 욕설 감지 결과 추가
        special_factors = []
        if profanity_detected:
            label = profanity_category or "PROFANITY"
            special_factors.append((label, profanity_confidence))
        
        # Baseline 결과 추가
        special_factors.extend(baseline_results)
        
        # ==========================================
        # 2단계: AI hub 모델 기반 검증
        # ==========================================
        aihub_is_immoral = False
        aihub_confidence = 0.0
        aihub_type = None
        aihub_type_confidence = 0.0
        
        # AI hub 모델 신뢰도 threshold 설정
        MIN_AIHUB_CONFIDENCE_THRESHOLD = 0.7  # 최소 신뢰도 (Baseline 규칙과 일치 시)
        HIGH_AIHUB_CONFIDENCE_THRESHOLD = 0.9  # 높은 신뢰도 (Baseline 규칙과 불일치 시)
        
        if self.aihub_model:
            try:
                # AI hub 모델 1: is_immoral 판단
                aihub_is_immoral, aihub_confidence = self.aihub_model.predict_immoral(text)
                
                if aihub_is_immoral:
                    # Baseline 규칙과의 일치성 체크
                    baseline_detected = len(baseline_results) > 0 or profanity_detected
                    
                    # Baseline 규칙과의 일치 여부에 따라 다른 threshold 적용
                    if baseline_detected:
                        # Baseline 규칙에서도 감지된 경우: 일반 threshold 사용
                        required_confidence = MIN_AIHUB_CONFIDENCE_THRESHOLD
                    else:
                        # Baseline 규칙에서 감지되지 않은 경우: 높은 threshold 사용
                        # (잘못된 분류 방지: 예: '감사합니다. 좋은 서비스였어요' 같은 경우)
                        required_confidence = HIGH_AIHUB_CONFIDENCE_THRESHOLD
                        logger.debug(
                            f"Baseline 규칙과 불일치: AI hub 모델만 감지, "
                            f"높은 신뢰도 필요 (>= {required_confidence:.2f}), "
                            f"현재 신뢰도: {aihub_confidence:.4f}"
                        )
                    
                    if aihub_confidence >= required_confidence:
                        # AI hub 모델 2: 비도덕 유형 분류
                        aihub_type = self.aihub_model.predict_type(text)
                        aihub_type_confidence = self.aihub_model.get_confidence(text, aihub_type)
                        
                        # 타입 분류 신뢰도도 체크
                        if aihub_type_confidence >= MIN_AIHUB_CONFIDENCE_THRESHOLD:
                            # AI hub 모델 결과를 Special Label로 매핑
                            mapped_label = self._map_aihub_type_to_label(aihub_type)
                            if mapped_label:
                                # AI hub 모델의 신뢰도를 반영하여 추가
                                special_factors.append((mapped_label, aihub_confidence * 0.9))
                        else:
                            logger.debug(
                                f"AI hub 모델 타입 분류 신뢰도가 낮아 무시: "
                                f"type={aihub_type}, confidence={aihub_type_confidence:.4f} "
                                f"< {MIN_AIHUB_CONFIDENCE_THRESHOLD:.2f}"
                            )
                    else:
                        logger.debug(
                            f"AI hub 모델 is_immoral 신뢰도가 낮아 무시: "
                            f"confidence={aihub_confidence:.4f} < {required_confidence:.2f}"
                        )
            except Exception as e:
                logger.warning(f"AI hub 모델 검증 실패: {e}")
        
        # ==========================================
        # 최종 Label 결정
        # ==========================================
        if special_factors:
            # 가장 높은 신뢰도의 Label 선택
            primary_label, primary_confidence = max(special_factors, key=lambda x: x[1])
            
            # 모든 요인들을 합산하여 신뢰도 계산
            total_confidence = sum(conf for _, conf in special_factors)
            factor_count = len(special_factors)
            final_confidence = min(
                max(primary_confidence, total_confidence / factor_count) * (1.0 + (factor_count - 1) * 0.1),
                1.0
            )
            
            # probabilities 계산
            probabilities = {}
            total_factor_confidence = sum(conf for _, conf in special_factors)
            if total_factor_confidence > 0:
                for label, conf in special_factors:
                    probabilities[label] = conf / total_factor_confidence
            
            # ClassificationResult 생성
            classification_result = ClassificationResult(
                label=primary_label,
                label_type=LabelType.SPECIAL.value,
                confidence=final_confidence,
                text=text,
                probabilities=probabilities,
                timestamp=datetime.now()
            )
            
            # AI hub 모델 결과 메타데이터 추가
            if not hasattr(classification_result, 'metadata') or classification_result.metadata is None:
                classification_result.metadata = {}
            
            # AI Hub 모델 결과를 metadata에 저장 (DB 저장 시 사용)
            classification_result.metadata['aihub_is_immoral'] = aihub_is_immoral
            classification_result.metadata['aihub_confidence'] = aihub_confidence
            classification_result.metadata['aihub_type'] = aihub_type
            classification_result.metadata['aihub_type_confidence'] = aihub_type_confidence
            
            if aihub_is_immoral:
                classification_result.is_immoral = True
                classification_result.immorality_confidence = aihub_confidence
            
            return classification_result
        
        # Special Label이 아닌 경우: Normal Label로 분류
        label = "INQUIRY"  # 기본 Normal Label
        
        classification_result = ClassificationResult(
            label=label,
            label_type=LabelType.NORMAL.value,
            confidence=0.3,
            text=text,
            probabilities={label: 1.0},
            timestamp=datetime.now()
        )
        
        # AI hub 모델 결과가 False인 경우 명시적으로 설정
        if not hasattr(classification_result, 'metadata') or classification_result.metadata is None:
            classification_result.metadata = {}
        
        # AI Hub 모델 결과를 metadata에 저장 (항상 저장)
        classification_result.metadata['aihub_is_immoral'] = aihub_is_immoral
        classification_result.metadata['aihub_confidence'] = aihub_confidence
        classification_result.metadata['aihub_type'] = aihub_type
        classification_result.metadata['aihub_type_confidence'] = aihub_type_confidence
        
        if self.aihub_model and not aihub_is_immoral:
            classification_result.is_immoral = False
            classification_result.immorality_confidence = aihub_confidence
        
        return classification_result
    
    def _map_aihub_type_to_label(self, aihub_type: str) -> Optional[str]:
        """
        AI hub 모델의 비도덕 유형을 Special Label로 매핑
        
        Args:
            aihub_type: AI hub 모델 예측 유형 (VIOLENCE, SEXUAL, ABUSE, DISCRIMINATION, IMMORAL_NONE)
        
        Returns:
            Special Label 또는 None
        """
        mapping = {
            "VIOLENCE": "VIOLENCE_THREAT",
            "SEXUAL": "SEXUAL_HARASSMENT",
            "ABUSE": "PROFANITY",
            "DISCRIMINATION": "HATE_SPEECH",
            "IMMORAL_NONE": None
        }
        return mapping.get(aihub_type)
    
    def is_special_label(self, result: ClassificationResult) -> bool:
        """
        결과가 Special Label인지 확인
        
        Args:
            result: ClassificationResult (validate 메서드의 반환값)
        
        Returns:
            bool: Special Label 여부
                - True: label_type이 "SPECIAL"인 경우
                - False: label_type이 "NORMAL"인 경우
        
        Note:
            이 메서드는 MainPipeline에서 두 번째 세션으로 전달할지 결정하는 데 사용됩니다.
        """
        if result is None:
            return False
        return result.label_type == LabelType.SPECIAL.value
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        세션 정보 반환 (디버깅 및 모니터링용)
        
        Returns:
            Dict: 세션 상태 정보
        """
        return {
            'has_baseline_rules': self.baseline_rules is not None,
            'has_aihub_model': self.aihub_model is not None,
            'session_type': 'BaselineValidationSession'
        }

