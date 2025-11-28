"""
Final Score Calculation Session (세 번째 세션)

후반부 처리:
- 첫 번째 세션 결과 (BaselineValidationSession)와 두 번째 세션 결과 (IntensityValidationSession)를 종합
- 최종 점수 계산 (score_risk, score_profanity, score_threat 등)
- 최종 label 및 confidence 조정
- Feature Extractor를 사용한 baseline 점수 계산 통합

의존성:
- ClassificationResult: 결과 데이터 구조 (필수)
- ProfanityResult: 욕설 감지 결과 (선택적)
- LabelType: 라벨 타입 정의 (필수)
- CustomerFeatureExtractor: Feature 기반 점수 계산 (선택적)
- ProfanityDetector: 욕설 감지 (선택적)
- session_utils: 검증 함수들 (필수)
"""

from typing import Dict, Optional, Any, Tuple
from datetime import datetime
import logging

from ..data.data_structures import ClassificationResult, ProfanityResult
from ..config.labels import LabelType, SPECIAL_LABELS
from .session_utils import validate_score, validate_text, validate_label, validate_label_type

# Feature Extractor (선택적 import)
try:
    from ..feature_extractor.customer_feature_extractor import CustomerFeatureExtractor
    from ..profanity_filter.profanity_detector import ProfanityDetector
except ImportError:
    CustomerFeatureExtractor = None
    ProfanityDetector = None

logger = logging.getLogger(__name__)


class FinalScoreCalculationSession:
    """
    Final Score Calculation Session
    
    세 번째 세션:
    - 첫 번째 세션 결과와 두 번째 세션 결과를 종합
    - 최종 점수 계산
    - 최종 label 및 confidence 조정
    """
    
    def __init__(
        self,
        use_feature_extractor: bool = True,
        profanity_detector: Optional[Any] = None,
        feature_extractor: Optional[Any] = None
    ):
        """
        Final Score Calculation Session 초기화
        
        초기화 우선순위:
        1. 인스턴스 직접 전달 (profanity_detector, feature_extractor)
        2. 자동 생성 (CustomerFeatureExtractor, ProfanityDetector)
        3. None (사용 안 함)
        
        Args:
            use_feature_extractor: Feature Extractor 사용 여부 (기본: True)
            profanity_detector: ProfanityDetector 인스턴스 (선택적, 우선순위 1)
            feature_extractor: CustomerFeatureExtractor 인스턴스 (선택적, 우선순위 1)
        
        Raises:
            None (에러 발생 시 경고 로그만 출력하고 계속 진행)
        """
        self.use_feature_extractor = use_feature_extractor
        
        # Feature Extractor 초기화 (우선순위: feature_extractor > 자동 생성 > None)
        if use_feature_extractor:
            if feature_extractor:
                self.feature_extractor = feature_extractor
                logger.debug("CustomerFeatureExtractor 인스턴스를 직접 사용합니다.")
            elif CustomerFeatureExtractor:
                self.feature_extractor = CustomerFeatureExtractor()
                logger.debug("CustomerFeatureExtractor 자동 생성 완료.")
            else:
                self.feature_extractor = None
                logger.warning("CustomerFeatureExtractor를 사용할 수 없습니다. label 기반 점수 계산만 사용합니다.")
        else:
            self.feature_extractor = None
            logger.debug("Feature Extractor를 사용하지 않습니다.")
        
        # Profanity Detector 초기화 (우선순위: profanity_detector > 자동 생성 > None)
        if profanity_detector:
            self.profanity_detector = profanity_detector
            logger.debug("ProfanityDetector 인스턴스를 직접 사용합니다.")
        elif ProfanityDetector:
            self.profanity_detector = ProfanityDetector()
            logger.debug("ProfanityDetector 자동 생성 완료.")
        else:
            self.profanity_detector = None
            logger.debug("ProfanityDetector를 사용하지 않습니다.")
    
    def calculate_final_scores(
        self,
        classification_result: ClassificationResult,
        text: str,
        use_feature_extractor: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        최종 점수 계산
        
        처리 순서:
        1. 기본 점수 계산 (Feature Extractor 또는 label 기반)
        2. Intensity 기반 점수 조정 (두 번째 세션 결과 반영)
        3. 종합 리스크 점수 계산 (모든 카테고리 점수의 최대값)
        4. 최종 label 및 confidence 조정 (점수 기반)
        5. 점수 상세 내역 생성
        
        Args:
            classification_result: 첫 번째와 두 번째 세션을 거친 ClassificationResult
                - label, label_type, confidence: 첫 번째 세션 결과
                - intensity, intensity_level, is_immoral: 두 번째 세션 결과 (Special label만)
            text: 원본 텍스트 (Feature Extractor 사용 시 필요)
            use_feature_extractor: Feature Extractor 사용 여부 (None이면 초기화 시 설정값 사용)
        
        Returns:
            Dict[str, Any]: 최종 점수 딕셔너리
                - score_risk: float (0.0 ~ 1.0) - 종합 리스크 점수
                - score_profanity: float (0.0 ~ 1.0) - 욕설 점수
                - score_threat: float (0.0 ~ 1.0) - 위협 점수
                - score_unreasonable_demand: float (0.0 ~ 1.0) - 무리한 요구 점수
                - score_sexual_harassment: float (0.0 ~ 1.0) - 성희롱 점수
                - score_hate_speech: float (0.0 ~ 1.0) - 혐오표현 점수
                - score_repetition: float (0.0 ~ 1.0) - 반복 점수
                - final_label: str - 최종 label (조정된 경우)
                - final_confidence: float (0.0 ~ 1.0) - 최종 confidence
                - score_breakdown: Dict - 점수 상세 내역 (base_scores, intensity_adjustment 등)
        
        Note:
            - Feature Extractor를 사용하면 더 정확한 baseline 점수 계산 가능
            - Intensity 정보가 있으면 점수 조정 수행
            - Special label인 경우 점수 기반으로 label 조정 가능
        """
        # ==========================================
        # 1단계: 기본 점수 계산
        # ==========================================
        # Feature Extractor 사용 여부 결정
        use_fe = use_feature_extractor if use_feature_extractor is not None else self.use_feature_extractor
        
        if use_fe and self.feature_extractor:
            # Feature Extractor를 사용한 baseline 점수 계산
            base_scores = self._calculate_scores_with_feature_extractor(
                text=text,
                classification_result=classification_result
            )
        else:
            # label 기반 기본 점수 계산
            base_scores = self._calculate_base_scores(classification_result)
        
        # ==========================================
        # 2단계: Intensity 기반 점수 조정
        # ==========================================
        intensity_adjusted_scores = self._adjust_scores_by_intensity(
            base_scores,
            classification_result
        )
        
        # ==========================================
        # 3단계: 종합 리스크 점수 계산
        # ==========================================
        final_scores = self._calculate_final_risk_score(intensity_adjusted_scores)
        
        # ==========================================
        # 4단계: 최종 label 및 confidence 조정
        # ==========================================
        final_label, final_confidence = self._adjust_final_label_and_confidence(
            classification_result,
            final_scores
        )
        
        # ==========================================
        # 5단계: 점수 상세 내역 생성
        # ==========================================
        score_breakdown = self._create_score_breakdown(
            classification_result,
            base_scores,
            intensity_adjusted_scores,
            final_scores
        )
        
        # extracted_features를 반환값에 포함 (solution_system 호환성)
        extracted_features = None
        if hasattr(classification_result, 'metadata') and classification_result.metadata:
            extracted_features = classification_result.metadata.get('extracted_features', {})
        
        return {
            'score_risk': final_scores['score_risk'],
            'score_profanity': final_scores['score_profanity'],
            'score_threat': final_scores['score_threat'],
            'score_unreasonable_demand': final_scores['score_unreasonable_demand'],
            'score_sexual_harassment': final_scores['score_sexual_harassment'],
            'score_hate_speech': final_scores['score_hate_speech'],
            'score_repetition': final_scores['score_repetition'],
            'final_label': final_label,
            'final_confidence': final_confidence,
            'score_breakdown': score_breakdown,
            'extracted_features': extracted_features or {}  # solution_system 호환성
        }
    
    def _calculate_scores_with_feature_extractor(
        self,
        text: str,
        classification_result: ClassificationResult
    ) -> Dict[str, float]:
        """
        Feature Extractor를 사용한 baseline 점수 계산
        
        Args:
            text: 분석할 텍스트
            classification_result: ClassificationResult 객체
        
        Returns:
            점수 딕셔너리
        """
        if not self.feature_extractor:
            # Feature Extractor가 없으면 기본 점수 계산
            return self._calculate_base_scores(classification_result)
        
        # ProfanityResult 생성
        profanity_result = None
        if self.profanity_detector:
            profanity_result = self.profanity_detector.detect(text)
        else:
            # profanity_detector가 없으면 classification_result에서 추론
            is_profanity = classification_result.label == "PROFANITY"
            profanity_result = ProfanityResult(
                is_profanity=is_profanity,
                category="PROFANITY" if is_profanity else None,
                confidence=classification_result.confidence if is_profanity else 0.0,
                method="baseline"
            )
        
        # Feature Extractor를 사용하여 점수 계산
        feature_scores, extracted_features = self.feature_extractor.extract_features(
            text=text,
            profanity_result=profanity_result,
            classification_result=classification_result
        )
        
        # feature_scores를 DB 필드명에 맞게 변환
        scores = {
            'score_profanity': feature_scores.get('profanity_score', 0.0),
            'score_threat': feature_scores.get('threat_score', 0.0),
            'score_unreasonable_demand': feature_scores.get('unreasonable_demand_score', 0.0),
            'score_sexual_harassment': feature_scores.get('sexual_harassment_score', 0.0),
            'score_hate_speech': feature_scores.get('hate_speech_score', 0.0),
            'score_repetition': feature_scores.get('repetition_keyword_score', 0.0),
        }
        
        # 종합 리스크 점수 계산 (최대값 사용)
        scores['score_risk'] = max(
            scores['score_profanity'],
            scores['score_threat'],
            scores['score_unreasonable_demand'],
            scores['score_sexual_harassment'],
            scores['score_hate_speech'],
            scores['score_repetition']
        )
        
        # SPECIAL 라벨이면 최소 리스크 점수 보장
        if classification_result.label_type == "SPECIAL" and scores['score_risk'] < 0.3:
            confidence = classification_result.confidence or 0.0
            scores['score_risk'] = max(scores['score_risk'], confidence * 0.5)
        
        # extracted_features를 메타데이터에 저장 (solution_system 호환성)
        if not hasattr(classification_result, 'metadata') or classification_result.metadata is None:
            classification_result.metadata = {}
        classification_result.metadata['extracted_features'] = extracted_features
        
        return scores
    
    def _calculate_base_scores(
        self,
        classification_result: ClassificationResult
    ) -> Dict[str, float]:
        """
        기본 점수 계산 (label 기반)
        
        Args:
            classification_result: ClassificationResult
        
        Returns:
            기본 점수 딕셔너리
        """
        label = classification_result.label
        label_type = classification_result.label_type
        confidence = classification_result.confidence
        
        # 기본 점수 초기화
        base_scores = {
            'score_profanity': 0.0,
            'score_threat': 0.0,
            'score_unreasonable_demand': 0.0,
            'score_sexual_harassment': 0.0,
            'score_hate_speech': 0.0,
            'score_repetition': 0.0
        }
        
        # Special Label인 경우 label에 따라 점수 부여
        if label_type == LabelType.SPECIAL.value:
            if label == "PROFANITY":
                base_scores['score_profanity'] = confidence
            elif label == "VIOLENCE_THREAT":
                base_scores['score_threat'] = confidence
            elif label == "SEXUAL_HARASSMENT":
                base_scores['score_sexual_harassment'] = confidence
            elif label == "HATE_SPEECH":
                base_scores['score_hate_speech'] = confidence
            elif label == "UNREASONABLE_DEMAND":
                base_scores['score_unreasonable_demand'] = confidence
            elif label == "REPETITION":
                base_scores['score_repetition'] = confidence
        
        # probabilities에서 추가 점수 추출
        if classification_result.probabilities:
            for prob_label, prob_value in classification_result.probabilities.items():
                if prob_label == "PROFANITY":
                    base_scores['score_profanity'] = max(
                        base_scores['score_profanity'],
                        prob_value * 0.8
                    )
                elif prob_label == "VIOLENCE_THREAT":
                    base_scores['score_threat'] = max(
                        base_scores['score_threat'],
                        prob_value * 0.8
                    )
                elif prob_label == "SEXUAL_HARASSMENT":
                    base_scores['score_sexual_harassment'] = max(
                        base_scores['score_sexual_harassment'],
                        prob_value * 0.8
                    )
                elif prob_label == "HATE_SPEECH":
                    base_scores['score_hate_speech'] = max(
                        base_scores['score_hate_speech'],
                        prob_value * 0.8
                    )
                elif prob_label == "UNREASONABLE_DEMAND":
                    base_scores['score_unreasonable_demand'] = max(
                        base_scores['score_unreasonable_demand'],
                        prob_value * 0.8
                    )
                elif prob_label == "REPETITION":
                    base_scores['score_repetition'] = max(
                        base_scores['score_repetition'],
                        prob_value * 0.8
                    )
        
        return base_scores
    
    def _adjust_scores_by_intensity(
        self,
        base_scores: Dict[str, float],
        classification_result: ClassificationResult
    ) -> Dict[str, float]:
        """
        Intensity 기반 점수 조정
        
        Args:
            base_scores: 기본 점수
            classification_result: ClassificationResult (intensity 정보 포함)
        
        Returns:
            Intensity 조정된 점수
        """
        adjusted_scores = base_scores.copy()
        
        # Intensity 정보가 있는 경우 점수 조정
        if classification_result.intensity is not None:
            intensity = classification_result.intensity
            intensity_level = classification_result.intensity_level
            is_immoral = classification_result.is_immoral
            immorality_confidence = classification_result.immorality_confidence or 0.0
            
            # is_immoral이 True인 경우 점수 보정
            if is_immoral:
                # intensity를 0.0 ~ 1.0 범위로 정규화 (0.0 ~ 3.0 -> 0.0 ~ 1.0)
                intensity_normalized = min(intensity / 3.0, 1.0)
                
                # intensity_level에 따른 가중치
                level_weights = {
                    'LOW': 0.3,
                    'MEDIUM': 0.6,
                    'HIGH': 0.9,
                    'VERY_HIGH': 1.0
                }
                level_weight = level_weights.get(intensity_level, 0.5)
                
                # 각 점수에 intensity 기반 보정 적용
                for score_key in adjusted_scores:
                    if adjusted_scores[score_key] > 0.0:
                        # 기존 점수와 intensity 보정 점수를 결합
                        intensity_boost = intensity_normalized * level_weight * immorality_confidence
                        adjusted_scores[score_key] = min(
                            adjusted_scores[score_key] + intensity_boost * 0.3,
                            1.0
                        )
                    elif intensity_normalized > 0.5:
                        # 점수가 없지만 intensity가 높은 경우 최소 점수 부여
                        adjusted_scores[score_key] = intensity_normalized * level_weight * 0.5
        
        return adjusted_scores
    
    def _calculate_final_risk_score(
        self,
        adjusted_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        종합 리스크 점수 계산
        
        Args:
            adjusted_scores: Intensity 조정된 점수
        
        Returns:
            최종 점수 (score_risk 포함)
        """
        final_scores = adjusted_scores.copy()
        
        # 종합 리스크 점수 = 모든 점수의 최대값
        # 각 카테고리별 점수 중 가장 높은 값을 리스크 점수로 사용
        score_risk = max(
            final_scores['score_profanity'],
            final_scores['score_threat'],
            final_scores['score_unreasonable_demand'],
            final_scores['score_sexual_harassment'],
            final_scores['score_hate_speech'],
            final_scores['score_repetition']
        )
        
        final_scores['score_risk'] = min(score_risk, 1.0)
        
        return final_scores
    
    def _adjust_final_label_and_confidence(
        self,
        classification_result: ClassificationResult,
        final_scores: Dict[str, float]
    ) -> Tuple[str, float]:
        """
        최종 label 및 confidence 조정
        
        Args:
            classification_result: ClassificationResult
            final_scores: 최종 점수
        
        Returns:
            (final_label, final_confidence)
        """
        original_label = classification_result.label
        original_confidence = classification_result.confidence
        label_type = classification_result.label_type
        
        # Special Label인 경우 점수 기반으로 label 조정 가능
        if label_type == LabelType.SPECIAL.value:
            # 가장 높은 점수를 가진 카테고리로 label 조정
            score_mapping = {
                'score_profanity': 'PROFANITY',
                'score_threat': 'VIOLENCE_THREAT',
                'score_sexual_harassment': 'SEXUAL_HARASSMENT',
                'score_hate_speech': 'HATE_SPEECH',
                'score_unreasonable_demand': 'UNREASONABLE_DEMAND',
                'score_repetition': 'REPETITION'
            }
            
            # 가장 높은 점수 찾기
            max_score = 0.0
            max_score_key = None
            for score_key, score_value in final_scores.items():
                if score_key in score_mapping and score_value > max_score:
                    max_score = score_value
                    max_score_key = score_key
            
            # 점수가 충분히 높으면 label 조정
            if max_score_key and max_score > 0.6:
                suggested_label = score_mapping[max_score_key]
                # 원래 label과 다르고 점수가 더 높으면 조정
                if suggested_label != original_label and max_score > original_confidence:
                    final_label = suggested_label
                    final_confidence = max_score
                else:
                    final_label = original_label
                    final_confidence = max(original_confidence, max_score * 0.9)
            else:
                final_label = original_label
                final_confidence = original_confidence
        else:
            # Normal Label인 경우 그대로 유지
            final_label = original_label
            final_confidence = original_confidence
        
        return final_label, final_confidence
    
    def _create_score_breakdown(
        self,
        classification_result: ClassificationResult,
        base_scores: Dict[str, float],
        intensity_adjusted_scores: Dict[str, float],
        final_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        점수 상세 내역 생성
        
        Args:
            classification_result: ClassificationResult
            base_scores: 기본 점수
            intensity_adjusted_scores: Intensity 조정된 점수
            final_scores: 최종 점수
        
        Returns:
            점수 상세 내역 딕셔너리
        """
        breakdown = {
            'base_scores': base_scores.copy(),
            'intensity_adjustment': {},
            'final_scores': final_scores.copy(),
            'intensity_info': {
                'intensity': classification_result.intensity,
                'intensity_level': classification_result.intensity_level,
                'is_immoral': classification_result.is_immoral,
                'immorality_confidence': classification_result.immorality_confidence
            },
            'label_info': {
                'original_label': classification_result.label,
                'label_type': classification_result.label_type,
                'original_confidence': classification_result.confidence
            }
        }
        
        # Intensity 조정 내역 계산
        for key in base_scores:
            adjustment = intensity_adjusted_scores[key] - base_scores[key]
            if abs(adjustment) > 0.01:  # 0.01 이상 차이만 기록
                breakdown['intensity_adjustment'][key] = {
                    'before': base_scores[key],
                    'after': intensity_adjusted_scores[key],
                    'adjustment': adjustment
                }
        
        return breakdown
    
    def apply_final_scores_to_result(
        self,
        classification_result: ClassificationResult,
        final_scores: Dict[str, Any]
    ) -> ClassificationResult:
        """
        최종 점수를 ClassificationResult에 적용
        
        Args:
            classification_result: ClassificationResult
            final_scores: 최종 점수 딕셔너리
        
        Returns:
            최종 점수가 적용된 ClassificationResult
        """
        # label 및 confidence 업데이트 (검증 포함)
        classification_result.label = validate_label(
            final_scores['final_label'],
            default=classification_result.label
        )
        classification_result.confidence = validate_score(
            final_scores['final_confidence'],
            'final_confidence'
        )
        
        # label_type 검증
        classification_result.label_type = validate_label_type(
            classification_result.label,
            classification_result.label_type or "NORMAL"
        )
        
        # 메타데이터에 최종 점수 추가
        if not hasattr(classification_result, 'metadata') or classification_result.metadata is None:
            classification_result.metadata = {}
        
        classification_result.metadata['final_scores'] = {
            'score_risk': validate_score(final_scores['score_risk'], 'score_risk'),
            'score_profanity': validate_score(final_scores['score_profanity'], 'score_profanity'),
            'score_threat': validate_score(final_scores['score_threat'], 'score_threat'),
            'score_unreasonable_demand': validate_score(final_scores['score_unreasonable_demand'], 'score_unreasonable_demand'),
            'score_sexual_harassment': validate_score(final_scores['score_sexual_harassment'], 'score_sexual_harassment'),
            'score_hate_speech': validate_score(final_scores['score_hate_speech'], 'score_hate_speech'),
            'score_repetition': validate_score(final_scores['score_repetition'], 'score_repetition')
        }
        classification_result.metadata['score_breakdown'] = final_scores['score_breakdown']
        
        return classification_result
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        세션 정보 반환 (디버깅 및 모니터링용)
        
        Returns:
            Dict: 세션 상태 정보
        """
        return {
            'use_feature_extractor': self.use_feature_extractor,
            'has_feature_extractor': self.feature_extractor is not None,
            'has_profanity_detector': self.profanity_detector is not None,
            'session_type': 'FinalScoreCalculationSession'
        }
    
    def is_available(self) -> bool:
        """
        세션이 사용 가능한지 확인
        
        Returns:
            bool: 항상 True (모델 없이도 작동 가능)
        """
        return True

