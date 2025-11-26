from typing import List, Optional
from ..schemas import SolutionRequestDTO  # DTO Import
from .data_structures import ResponseGuide
from .constants import get_sentiment_category

class SolutionGenerator:
    """
    상담 솔루션 생성기
    - Input: 분석된 세션 데이터 (Logical Label, Emotion Label, Risk Score, Keywords 등)
    - Output: ResponseGuide (전략, 톤앤매너, 스크립트)
    """

    def generate_guide(self, context: SolutionRequestDTO) -> ResponseGuide:
        # 0. Basic Guide 생성
        guide = ResponseGuide(
            strategy_title="기본 응대",
            strategy_description="고객의 문의 사항을 경청하고 친절하게 응대합니다.",
            tone_and_manner="친절하고 정중한 어조",
            checkpoints=["정확한 발음", "경청하는 태도"]
        )

        # 1. [최우선] Special Label 처리 (특수 상황)
        if context.logical_type == "SPECIAL":
            return self._generate_special_guide(context, guide)
            
        # 2. [차순위] 감정 카테고리별 처리 (Normal Label인 경우)
        if context.logical_type == "SPECIAL":
            return self._handle_special_situation(context, guide)

        return self._handle_normal_situation(context,guide)
    
    
    # Layer 1: 특수 상황 대응 (Safety & Legal)
    # =======================================================================
    def _handle_special_situation(self,context: SolutionRequestDTO, guide: ResponseGuide) -> ResponseGuide:
        # A. 성희롱 (Zero Tolerance)
        if context.profanity_category == "SEXUAL_HARASSMENT":
            guide.strategy_title = "🚨 성희롱 발언 감지: 무관용 원칙 및 법적 고지"
            guide.strategy_description = "감정적 동요 없이 단호하게 경고하고, 재발 시 통화를 종료합니다."
            guide.tone_and_manner = "감정이 배제된 건조하고 단호한(Dry & Firm) 어조"
            guide.required_keywords = ["성적 수치심", "법적 조치", "상담 종료", "경고"]
            guide.solution_scripts = [
                "고객님, 성적 수치심을 유발하는 발언은 법적 처벌 대상이 될 수 있습니다.",
                "지금 즉시 발언을 멈추지 않으시면 규정에 따라 상담이 종료됩니다."
            ]
            guide.checkpoints = ["녹취 고지 재확인", "ARD(자동응답) 이관 준비"]
            return guide
        
        # B. 위협/협박 (Risk Score에 따른 대응 수준 분기)
        if context.profanity_category == "VIOLENCE_THREAT":
            if context.risk_score >= 0.8: # 고위험: 실제 신변 위협
                guide.strategy_title = "👮 신변 위협 감지: 경찰 신고 고려 및 즉시 중단"
                guide.tone_and_manner = "매우 단호하고 침착한 어조"
                guide.solution_scripts = [
                    "고객님, 폭언과 협박이 지속되어 상담을 진행할 수 없습니다.",
                    "해당 발언은 녹취되어 법적 증거로 활용될 수 있음을 고지합니다. 통화를 종료합니다."
                ]
            else: # 저위험: 단순 으름장
                guide.strategy_title = "⚠️ 위협성 발언 경고 및 자제 요청"
                guide.solution_scripts = [
                    "고객님, 폭언은 삼가 주시길 부탁드립니다.",
                    "원활한 상담을 위해 언어 순화를 부탁드립니다."
                ]
            return guide
        
        # C. 욕설/모욕 (Category: INSULT)
        if context.profanity_category == "INSULT" or context.logical_label == "PROFANITY":
            guide.strategy_title = "🚫 욕설/비하 발언 대응"
            guide.tone_and_manner = "차분하지만 단호한 어조"
            guide.solution_scripts = ["고객님, 욕설을 하시면 상담 도움을 드리기가 어렵습니다."]
            return guide
        
        # D. 무리한 요구 (Keywords 활용 디테일)
        if context.logical_label == "UNREASONABLE_DEMAND":
            keywords = context.extracted_keywords.get("unreasonable_keywords", [])
            
            # 키워드별 맞춤 대응
            if any(k in ["공짜", "무료", "돈", "금전"] for k in keywords):
                guide.strategy_title = "💰 금전적 보상 요구에 대한 규정 안내"
                guide.solution_scripts = ["규정 외의 금전적 보상은 제공해 드리기 어렵습니다. 양해 부탁드립니다."]
            
            elif any(k in ["사장", "팀장", "책임자", "상급자"] for k in keywords):
                guide.strategy_title = "👔 상급자 통화 요구 대응"
                guide.tone_and_manner = "책임감 있고 신뢰감을 주는 어조"
                guide.solution_scripts = [
                    "제가 책임지고 안내해 드리고 있습니다. 말씀해 주시면 처리해 드리겠습니다.",
                    "담당자가 변경되어도 규정은 동일함을 안내해 드립니다."
                ]
            else:
                guide.strategy_title = "🚫 규정 외 요구사항 정중한 거절"
                guide.solution_scripts = ["죄송합니다만, 해당 요구사항은 도움 드리기 어렵습니다."]
            
            return guide
        
        guide.strategy_title = "특수 상황 대응"
        return guide
    

    # Layer 2: 일반상황 대응 (Normal Situation)
    # Risk Score을 통한 톤앤 매너 보정 -> 감정 카테고리 별 대응
    def _handle_normal_situation(self, context: SolutionRequestDTO, guide: ResponseGuide) -> ResponseGuide:
        
        # 1. Risk Score 기반 톤앤매너 보정 (Intensity Layer)
        # Normal Label이라도 리스크가 높으면(예: 매우 강한 불만) 일반 응대보다 더 조심해야 함
        if context.risk_score >= 0.7:
            guide.tone_and_manner = "매우 신중하고, 사과를 전제한 차분한 어조"
            guide.checkpoints.append("고객 감정 자극 금지")
        elif context.risk_score >= 0.4:
            guide.tone_and_manner = "적극적으로 공감하며 경청하는 어조"
        
        # 2. 감정 카테고리 기반 내용 생성 (Context Layer)
        sentiment_cat = get_sentiment_category(context.emotion_label)

        if sentiment_cat == "NEGATIVE_HIGH":
            self._fill_high_negative_content(context, guide)
        elif sentiment_cat == "NEGATIVE_LOW":
            self._fill_low_negative_content(context, guide)
        elif sentiment_cat == "POSITIVE":
            self._fill_positive_content(context, guide)
        else: # NEUTRAL
            self._fill_neutral_content(context, guide)
            
        return guide
    
    # 감정 카테고리 기반 내용 생성 로직 함수
    # sentiment_cat == "NEGATIVE_HIGH": 
    def _fill_high_negative_content(self, context: SolutionRequestDTO, guide: ResponseGuide):
        """격분, 분노 등"""
        guide.strategy_title = f"🔥 {context.emotion_label} 상태: 적극적 진정(De-escalation) 및 경청"
        guide.strategy_description = "고객의 말을 끊지 않고 끝까지 경청하여 감정을 해소(Ventilation)시킨 후 대화를 시도합니다."
        
        if context.logical_label == "COMPLAINT":
            guide.solution_scripts = [
                f"고객님, 많이 {context.emotion_label}하셨을 것 같습니다. 정말 죄송합니다.",
                "말씀해주신 부분 제가 꼼꼼히 확인하고 책임지고 도와드리겠습니다."
            ]
        elif context.logical_label == "REPETITION":
            guide.solution_scripts = ["네, 고객님 말씀 충분히 이해했습니다. 같은 문제로 불편 드려 죄송합니다."]

    # sentiment_cat == "NEGATIVE_LOW"
    def _fill_low_negative_content(self, context: SolutionRequestDTO, guide: ResponseGuide):
        """짜증, 실망, 슬픔 등"""
        guide.strategy_title = f"💧 {context.emotion_label} 상태: 공감적 해결 제시"
        guide.strategy_description = "불편 사항에 공감함을 표현하고, 신속한 해결책을 제시하여 신뢰를 회복합니다."
        
        # 세부 감정 디테일
        if context.emotion_label in ["무기력", "피로", "슬픔"]:
            guide.tone_and_manner = "따뜻하고 배려심 깊은 어조 (Soft)"
            guide.solution_scripts = ["많이 피곤하셨을 텐데, 제가 신속하게 처리해 드리겠습니다."]
        elif context.emotion_label in ["냉소", "불신"]:
            guide.strategy_title = "🛡️ 사실 기반의 신뢰 회복"
            guide.solution_scripts = ["우려하시는 점이 없도록 근거 자료를 통해 정확히 설명드리겠습니다."]
        else:
            guide.solution_scripts = ["이용에 불편을 드려 죄송합니다. 바로 확인해 드리겠습니다."]

    # sentiment_cat == "POSITIVE"
    def _fill_positive_content(self, context: SolutionRequestDTO, guide: ResponseGuide):
        """기쁨, 감사 등"""
        guide.strategy_title = f"✨ {context.emotion_label} 상태: 라포(Rapport) 형성 및 긍정 경험 강화"
        guide.tone_and_manner = "밝고 활기찬 어조 (High Energy)"
        
        if context.emotion_label in ["칭찬", "진심 어린 감사"]:
            guide.solution_scripts = [
                "고객님의 따뜻한 말씀 덕분에 제가 더 힘이 납니다. 감사합니다!",
                "앞으로도 만족스러운 서비스를 위해 최선을 다하겠습니다."
            ]
        else:
            guide.solution_scripts = ["만족하셨다니 다행입니다. 더 궁금하신 점은 없으신가요?"]

    # NEUTRAL
    def _fill_neutral_content(self, context: SolutionRequestDTO, guide: ResponseGuide):
        """중립"""
        guide.strategy_title = "ℹ️ 정확하고 신속한 정보 전달"
        guide.strategy_description = "군더더기 없이 고객이 원하는 정보를 정확하게 파악하여 제공합니다."
        
        if context.logical_label == "INQUIRY":
            guide.solution_scripts = ["문의하신 내용 확인 후 바로 안내해 드리겠습니다."]
        elif context.logical_label == "CLARIFICATION":
            guide.solution_scripts = ["제가 이해한 내용이 맞는지 다시 한번 확인해 드리겠습니다."]
        else:
            guide.solution_scripts = ["네, 고객님. 무엇을 도와드릴까요?"]