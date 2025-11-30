# logical_analysis/solution_system/logic/solution_generator.py

from ..schemas import SolutionRequestDTO
from .data_structures import ResponseGuide
from .constants import get_sentiment_category, SentimentType, IntensityLevel, LogicalType

class SolutionGenerator:
    """
    [개편된 솔루션 생성기]
    - 입력 감정이 단순('부정')하더라도, Intensity를 통해 '분노'와 '우울'을 구분하여 대응합니다.
    """

    def generate_guide(self, context: SolutionRequestDTO) -> ResponseGuide:
        guide = ResponseGuide(
            strategy_title="기본 응대",
            strategy_description="고객의 말씀을 경청하고 친절하게 응대합니다.",
            tone_and_manner="정중하고 차분한 어조",
            checkpoints=["정확한 발음", "쿠션어 사용"]
        )

        # 1. [최우선] 특수/위험 상황 (법적 이슈, 비도덕성)
        if context.logical_type == LogicalType.SPECIAL or context.is_immoral:
            return self._handle_special_situation(context, guide)

        # 2. [차순위] 고강도 감정 (격앙됨)
        if context.intensity_level == IntensityLevel.HIGH:
            return self._handle_high_intensity(context, guide)

        # 3. [기본] 일반 상황
        return self._handle_normal_situation(context, guide)

    # -------------------------------------------------------------
    # Handler 1: 특수 상황 (Special / Immoral)
    # -------------------------------------------------------------
    def _handle_special_situation(self, context: SolutionRequestDTO, guide: ResponseGuide) -> ResponseGuide:
        # A. 성희롱
        if context.profanity_category == "SEXUAL_HARASSMENT" or context.logical_label == "SEXUAL_HARASSMENT":
            guide.strategy_title = "🚨 성희롱 발언: 무관용 원칙 대응"
            guide.tone_and_manner = "건조하고 단호한(Dry & Firm) 어조"
            guide.solution_scripts = ["성적 수치심을 유발하는 발언은 법적 처벌 대상입니다. 중단해 주십시오."]
            return guide

        # B. 욕설/폭언 (강도에 따라 대응 분리)
        if context.logical_label in ["THREAT", "PROFANITY"] or context.profanity_category == "VIOLENCE_THREAT":
            if context.intensity_level == IntensityLevel.HIGH:
                guide.strategy_title = "👮 고성 및 폭언: 상담 중단 경고"
                guide.tone_and_manner = "크고 명확하며 단호한 목소리"
                guide.solution_scripts = ["고객님! 욕설과 고성은 삼가 주십시오. 상담이 불가능합니다."]
            else:
                guide.strategy_title = "🚫 인격 모독성 발언 차단"
                guide.tone_and_manner = "차분하지만 냉정한 어조"
                guide.solution_scripts = ["상담사에게 모욕감을 주는 언어 사용은 자제 부탁드립니다."]
            return guide

        # C. 비도덕적 화법 (비꼼, 무시)
        if context.is_immoral:
            guide.strategy_title = "🛡️ 비윤리적 화법(비꼼/무시) 대응"
            guide.strategy_description = "감정적으로 동요하지 말고, 객관적 사실(Fact) 위주로만 건조하게 안내하세요."
            guide.tone_and_manner = "사무적이고 건조한 어조 (감정 교류 최소화)"
            guide.solution_scripts = ["개인적인 비난은 문제 해결에 도움이 되지 않습니다. 규정에 대해 안내해 드리겠습니다."]
            return guide
        
        return guide

    # -------------------------------------------------------------
    # Handler 2: 고강도 감정 (High Intensity Normal)
    # -------------------------------------------------------------
    def _handle_high_intensity(self, context: SolutionRequestDTO, guide: ResponseGuide) -> ResponseGuide:
        sentiment = get_sentiment_category(context.emotion_label)

        # 부정 + High Intensity = '분노/격분'
        if sentiment == SentimentType.NEGATIVE:
            guide.strategy_title = "🔥 격앙된 고객: 적극적 진정(Ventilation) 유도"
            guide.strategy_description = "고객이 매우 흥분한 상태입니다. 해결책 제시보다 우선 끝까지 들어주며 에너지를 낮춰주세요."
            guide.tone_and_manner = "차분하고 낮은 톤, 평소보다 느린 속도"
            guide.solution_scripts = [
                "고객님, 많이 답답하셨겠습니다. 그 마음 충분히 이해합니다.",
                "우선 진정하시고 천천히 말씀해 주시면 제가 끝까지 도와드리겠습니다."
            ]
        
        # 긍정 + High Intensity = '큰 기쁨/흥분'
        elif sentiment == SentimentType.POSITIVE:
            guide.strategy_title = "✨ 높은 텐션의 긍정: 에너지 미러링(Mirroring)"
            guide.tone_and_manner = "활기차고 높은 톤 (High Energy)"
            guide.solution_scripts = ["와! 정말 다행이네요 고객님! 저도 너무 기쁩니다!"]

        return guide

    # -------------------------------------------------------------
    # Handler 3: 일반 상황 (Normal / Low~Mid Intensity)
    # -------------------------------------------------------------
    def _handle_normal_situation(self, context: SolutionRequestDTO, guide: ResponseGuide) -> ResponseGuide:
        sentiment = get_sentiment_category(context.emotion_label)

        # A. 부정 (Low~Mid Intensity) = '불만/실망/우울'
        if sentiment == SentimentType.NEGATIVE:
            guide.strategy_title = "💧 불편 사항에 대한 공감 및 신속 해결"
            guide.tone_and_manner = "따뜻하고 부드러운 어조 (Soft & Care)"
            guide.solution_scripts = [
                "이용에 불편을 드려 죄송합니다. 많이 번거로우셨죠?",
                "해당 부분은 제가 바로 확인해서 신속하게 처리해 드리겠습니다."
            ]

        # B. 긍정
        elif sentiment == SentimentType.POSITIVE:
            guide.strategy_title = "🤝 감사 표현 및 라포 형성"
            guide.solution_scripts = ["칭찬해 주셔서 감사합니다. 더 노력하는 상담사가 되겠습니다."]

        # C. 중립 (문의)
        else:
            if context.logical_label == "INQUIRY":
                guide.strategy_title = "ℹ️ 정확하고 간결한 정보 전달"
                guide.solution_scripts = ["문의하신 내용에 대해 바로 안내해 드리겠습니다."]
            else:
                guide.strategy_title = "🎧 적극적 경청 대기"
                guide.solution_scripts = ["네, 고객님. 무엇을 도와드릴까요?"]

        return guide