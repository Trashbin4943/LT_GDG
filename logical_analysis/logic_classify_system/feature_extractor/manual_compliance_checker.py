"""
매뉴얼 준수도 검사기

Keyword 기반으로 상담원 발화가 매뉴얼을 얼마나 준수했는지 평가
작은 조각 단위(키워드/구)로 문장 내 포함 여부 확인
"""

from typing import Dict, List, Set, Tuple, Any
import re
from ..config.manual_keywords import ManualKeywordConfig, ManualKeywords


class ManualComplianceChecker:
    """매뉴얼 준수도 검사기"""
    
    def __init__(self):
        """매뉴얼 준수도 검사기 초기화"""
        self.keyword_config = ManualKeywordConfig()
    
    def check_compliance(
        self,
        agent_text: str,
        emotion_label: str,
        customer_label: str,
        is_start: bool = False,  # 세션 시작 여부
        is_end: bool = False     # 세션 종료 여부
    ) -> Tuple[float, Dict[str, Any]]:
        """
        매뉴얼 준수도 검사
        
        Args:
            agent_text: 상담원 발화 텍스트
            emotion_label: 감정 라벨
            customer_label: 손님 발화 Label (CAR)
            is_start: 세션 시작 여부 (인사 확인용)
            is_end: 세션 종료 여부 (마무리 확인용)
        
        Returns:
            (compliance_score, compliance_details)
            - compliance_score: 매뉴얼 준수도 (0.0-1.0)
            - compliance_details: 상세 정보
        """
        # 매뉴얼 키워드 가져오기
        manual_keywords = self.keyword_config.get_keywords(emotion_label, customer_label)
        
        # 텍스트 전처리 (소문자 변환 및 공백 정규화)
        text_normalized = self._normalize_text(agent_text)
        
        # 1. 인사 키워드 검사 (시작/끝)
        greeting_score, greeting_details = self._check_greeting(
            text_normalized, manual_keywords, is_start
        )
        
        closing_score, closing_details = self._check_closing(
            text_normalized, manual_keywords, is_end
        )
        
        # 2. 필수 키워드 검사 (작은 조각 단위)
        required_score, required_details = self._check_required_keywords(
            text_normalized, manual_keywords
        )
        
        # 3. 금지 키워드 검사
        prohibited_score, prohibited_details = self._check_prohibited_keywords(
            text_normalized, manual_keywords
        )
        
        # 4. 응대 표현 검사 (구 단위)
        response_score, response_details = self._check_response_phrases(
            text_normalized, manual_keywords
        )
        
        # 5. 공감 표현 검사 (empathy_score와 겹치는 부분)
        empathy_score, empathy_details = self._check_empathy_phrases(
            text_normalized, manual_keywords
        )
        
        # 종합 점수 계산
        compliance_score = self._calculate_overall_score(
            greeting_score=greeting_score if is_start else None,
            closing_score=closing_score if is_end else None,
            required_score=required_score,
            prohibited_score=prohibited_score,  # 금지 키워드 사용 시 감점
            response_score=response_score,
            empathy_score=empathy_score
        )
        
        # 상세 정보 구성
        compliance_details = {
            "greeting_score": greeting_score,
            "greeting_details": greeting_details,
            "closing_score": closing_score,
            "closing_details": closing_details,
            "required_keyword_score": required_score,
            "required_keyword_details": required_details,
            "prohibited_keyword_score": prohibited_score,
            "prohibited_keyword_details": prohibited_details,
            "response_phrase_score": response_score,
            "response_phrase_details": response_details,
            "empathy_phrase_score": empathy_score,
            "empathy_phrase_details": empathy_details,
            "found_keywords": required_details.get("found_keywords", []),
            "missing_keywords": required_details.get("missing_keywords", []),
            "found_prohibited": prohibited_details.get("found_prohibited", []),
            "complied_items": self._get_complied_items(
                greeting_details, closing_details, required_details,
                response_details, empathy_details
            ),
            "non_complied_items": self._get_non_complied_items(
                greeting_details, closing_details, required_details,
                prohibited_details, response_details, empathy_details
            )
        }
        
        return compliance_score, compliance_details
    
    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (소문자 변환, 공백 정규화)"""
        # 소문자 변환 (한글은 영향 없음, 영문만)
        text = text.lower()
        # 공백 정규화
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _check_greeting(
        self,
        text: str,
        manual_keywords: ManualKeywords,
        is_start: bool
    ) -> Tuple[float, Dict[str, Any]]:
        """
        시작 인사 검사
        
        Returns:
            (score, details)
        """
        if not is_start:
            return 1.0, {"checked": False, "reason": "세션 시작이 아님"}
        
        found_keywords = []
        for keyword in manual_keywords.greeting_keywords:
            if self._contains_keyword(text, keyword):
                found_keywords.append(keyword)
        
        if found_keywords:
            score = min(1.0, len(found_keywords) / max(1, len(manual_keywords.greeting_keywords)))
            return score, {
                "checked": True,
                "found_keywords": found_keywords,
                "all_keywords": manual_keywords.greeting_keywords
            }
        else:
            return 0.0, {
                "checked": True,
                "found_keywords": [],
                "all_keywords": manual_keywords.greeting_keywords,
                "missing": True
            }
    
    def _check_closing(
        self,
        text: str,
        manual_keywords: ManualKeywords,
        is_end: bool
    ) -> Tuple[float, Dict[str, Any]]:
        """
        마무리 인사 검사
        
        Returns:
            (score, details)
        """
        if not is_end:
            return 1.0, {"checked": False, "reason": "세션 종료가 아님"}
        
        found_keywords = []
        for keyword in manual_keywords.closing_keywords:
            if self._contains_keyword(text, keyword):
                found_keywords.append(keyword)
        
        if found_keywords:
            score = min(1.0, len(found_keywords) / max(1, len(manual_keywords.closing_keywords)))
            return score, {
                "checked": True,
                "found_keywords": found_keywords,
                "all_keywords": manual_keywords.closing_keywords
            }
        else:
            return 0.0, {
                "checked": True,
                "found_keywords": [],
                "all_keywords": manual_keywords.closing_keywords,
                "missing": True
            }
    
    def _check_required_keywords(
        self,
        text: str,
        manual_keywords: ManualKeywords
    ) -> Tuple[float, Dict[str, Any]]:
        """
        필수 키워드 검사 (작은 조각 단위로 포함 여부 확인)
        
        Returns:
            (score, details)
        """
        if not manual_keywords.required_keywords:
            return 1.0, {"checked": False, "reason": "필수 키워드 없음"}
        
        found_keywords = []
        missing_keywords = []
        
        for keyword in manual_keywords.required_keywords:
            if self._contains_keyword(text, keyword):
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        # 필수 키워드 포함 비율로 점수 계산
        if len(manual_keywords.required_keywords) == 0:
            score = 1.0
        else:
            found_ratio = len(found_keywords) / len(manual_keywords.required_keywords)
            # 필수 키워드는 모두 포함되어야 높은 점수
            # 부분 점수: 0.5 (50% 포함) ~ 1.0 (100% 포함)
            if found_ratio == 1.0:
                score = 1.0
            elif found_ratio >= 0.5:
                score = 0.5 + (found_ratio - 0.5) * 1.0  # 0.5 ~ 1.0
            else:
                score = found_ratio * 1.0  # 0.0 ~ 0.5
        
        return score, {
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "all_keywords": manual_keywords.required_keywords,
            "found_count": len(found_keywords),
            "total_count": len(manual_keywords.required_keywords)
        }
    
    def _check_prohibited_keywords(
        self,
        text: str,
        manual_keywords: ManualKeywords
    ) -> Tuple[float, Dict[str, Any]]:
        """
        금지 키워드 검사
        
        Returns:
            (score, details) - score는 0.0이면 감점, 1.0이면 정상
        """
        if not manual_keywords.prohibited_keywords:
            return 1.0, {"checked": False, "reason": "금지 키워드 없음"}
        
        found_prohibited = []
        for keyword in manual_keywords.prohibited_keywords:
            if self._contains_keyword(text, keyword):
                found_prohibited.append(keyword)
        
        if found_prohibited:
            # 금지 키워드 사용 시 점수 0.0
            return 0.0, {
                "found_prohibited": found_prohibited,
                "all_prohibited": manual_keywords.prohibited_keywords
            }
        else:
            return 1.0, {
                "found_prohibited": [],
                "all_prohibited": manual_keywords.prohibited_keywords
            }
    
    def _check_response_phrases(
        self,
        text: str,
        manual_keywords: ManualKeywords
    ) -> Tuple[float, Dict[str, Any]]:
        """
        응대 표현 검사 (구 단위)
        
        Returns:
            (score, details)
        """
        if not manual_keywords.response_phrases:
            return 1.0, {"checked": False, "reason": "응대 표현 없음"}
        
        found_phrases = []
        for phrase in manual_keywords.response_phrases:
            if self._contains_keyword(text, phrase):
                found_phrases.append(phrase)
        
        if found_phrases:
            score = min(1.0, len(found_phrases) / max(1, len(manual_keywords.response_phrases)))
            return score, {
                "found_phrases": found_phrases,
                "all_phrases": manual_keywords.response_phrases
            }
        else:
            # 응대 표현은 필수가 아니므로 부분 점수
            return 0.5, {
                "found_phrases": [],
                "all_phrases": manual_keywords.response_phrases
            }
    
    def _check_empathy_phrases(
        self,
        text: str,
        manual_keywords: ManualKeywords
    ) -> Tuple[float, Dict[str, Any]]:
        """
        공감 표현 검사 (empathy_score와 겹치는 부분)
        
        Returns:
            (score, details)
        """
        if not manual_keywords.empathy_phrases:
            return 1.0, {"checked": False, "reason": "공감 표현 없음"}
        
        found_phrases = []
        for phrase in manual_keywords.empathy_phrases:
            if self._contains_keyword(text, phrase):
                found_phrases.append(phrase)
        
        if found_phrases:
            score = min(1.0, len(found_phrases) / max(1, len(manual_keywords.empathy_phrases)))
            return score, {
                "found_phrases": found_phrases,
                "all_phrases": manual_keywords.empathy_phrases
            }
        else:
            # 공감 표현도 필수가 아니므로 부분 점수
            return 0.5, {
                "found_phrases": [],
                "all_phrases": manual_keywords.empathy_phrases
            }
    
    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """
        키워드 포함 여부 확인 (작은 조각 단위)
        
        부분 문자열 매칭으로 정확도 향상
        """
        # 정규화된 키워드
        keyword_normalized = keyword.lower().strip()
        
        # 직접 포함 확인
        if keyword_normalized in text:
            return True
        
        # 공백 제거 후 포함 확인 (예: "안녕하세요"와 "안녕하세요.")
        text_no_space = re.sub(r'[^\w가-힣]', '', text)
        keyword_no_space = re.sub(r'[^\w가-힣]', '', keyword_normalized)
        
        if keyword_no_space and keyword_no_space in text_no_space:
            return True
        
        return False
    
    def _calculate_overall_score(
        self,
        greeting_score: float = None,
        closing_score: float = None,
        required_score: float = None,
        prohibited_score: float = None,
        response_score: float = None,
        empathy_score: float = None
    ) -> float:
        """
        종합 점수 계산
        
        가중치:
        - required_keyword: 0.4 (필수)
        - greeting/closing: 0.2 (시작/끝 시 중요)
        - response_phrase: 0.2 (응대 표현)
        - empathy_phrase: 0.2 (공감 표현)
        - prohibited: 감점 (사용 시 점수 * 0.5)
        """
        scores = []
        weights = []
        
        # 필수 키워드 (가장 중요)
        if required_score is not None:
            scores.append(required_score)
            weights.append(0.4)
        
        # 인사 (시작/끝 시 중요)
        if greeting_score is not None:
            scores.append(greeting_score)
            weights.append(0.2)
        
        if closing_score is not None:
            scores.append(closing_score)
            weights.append(0.2)
        
        # 응대 표현
        if response_score is not None:
            scores.append(response_score)
            weights.append(0.2)
        
        # 공감 표현
        if empathy_score is not None:
            scores.append(empathy_score)
            weights.append(0.2)
        
        if not scores:
            return 0.5  # 기본 점수
        
        # 가중 평균 계산
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.5
        
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        overall_score = weighted_sum / total_weight
        
        # 금지 키워드 사용 시 감점
        if prohibited_score is not None and prohibited_score < 1.0:
            overall_score *= 0.5
        
        return min(max(overall_score, 0.0), 1.0)
    
    def _get_complied_items(
        self,
        greeting_details: Dict,
        closing_details: Dict,
        required_details: Dict,
        response_details: Dict,
        empathy_details: Dict
    ) -> List[str]:
        """준수한 항목 리스트"""
        complied = []
        
        if greeting_details.get("found_keywords"):
            complied.append(f"시작 인사: {', '.join(greeting_details['found_keywords'])}")
        
        if closing_details.get("found_keywords"):
            complied.append(f"마무리 인사: {', '.join(closing_details['found_keywords'])}")
        
        if required_details.get("found_keywords"):
            complied.append(f"필수 키워드 포함: {', '.join(required_details['found_keywords'])}")
        
        if response_details.get("found_phrases"):
            complied.append(f"응대 표현 사용: {', '.join(response_details['found_phrases'][:2])}")  # 최대 2개만
        
        if empathy_details.get("found_phrases"):
            complied.append(f"공감 표현 사용: {', '.join(empathy_details['found_phrases'][:2])}")  # 최대 2개만
        
        return complied
    
    def _get_non_complied_items(
        self,
        greeting_details: Dict,
        closing_details: Dict,
        required_details: Dict,
        prohibited_details: Dict,
        response_details: Dict,
        empathy_details: Dict
    ) -> List[str]:
        """미준수한 항목 리스트"""
        non_complied = []
        
        if greeting_details.get("missing"):
            non_complied.append("시작 인사 누락")
        
        if closing_details.get("missing"):
            non_complied.append("마무리 인사 누락")
        
        if required_details.get("missing_keywords"):
            non_complied.append(f"필수 키워드 누락: {', '.join(required_details['missing_keywords'][:3])}")  # 최대 3개만
        
        if prohibited_details.get("found_prohibited"):
            non_complied.append(f"금지 키워드 사용: {', '.join(prohibited_details['found_prohibited'])}")
        
        return non_complied

