import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .label_map import label_map
from .label_map import sentiment_map
from ..features.extract_features import extract_features
from .audio_emotion import SimpleLSTM
from ..preprocessing.stt_preprocessor import Turn

class UnifiedEmotionAnalyzer:
    def __init__(self, 
                 text_model_name="rattyrat0/kote-multilabel-model", 
                 audio_weights_path="./audio_emotion_model.pth"):
        # KoBERT tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "monologg/kobert",
            trust_remote_code=True
        )
        # 텍스트 감정 분석 모델
        self.text_model = AutoModelForSequenceClassification.from_pretrained(
            text_model_name,
            trust_remote_code=True
        )
        self.text_model.eval()

        # 디바이스 설정
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.text_model.to(self.device)

        # 오디오 모델 로딩 (파일 없으면 비활성화)
        if os.path.exists(audio_weights_path):
            self.audio_model = SimpleLSTM(input_dim=23, num_classes=len(label_map))
            self.audio_model.load_state_dict(torch.load(audio_weights_path, map_location="cpu"))
            self.audio_model.eval()
        else:
            print("⚠️ audio_emotion_model.pth 파일이 없습니다. 오디오 분석 기능이 비활성화됩니다.")
            self.audio_model = None

    def analyze_text(self, text: str, threshold: float = 0.5):
        # 토큰화
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        ).to(self.device)

        # 모델 추론
        with torch.no_grad():
            outputs = self.text_model(**inputs)

        probs = torch.sigmoid(outputs.logits).detach().cpu().numpy()[0]
        labels = [label_map[i] for i, p in enumerate(probs) if p >= threshold]

        # ✅ 카테고리 매핑 적용
        sentiment_category = None
        for category, emotions in sentiment_map.items():
            if any(label in emotions for label in labels):
                sentiment_category = category
                break

        # 라벨이 없거나 매핑되지 않으면 중립 처리
        if sentiment_category is None:
            sentiment_category = "중립"

        return {
            "type": "text",
            "labels": labels,
            "probs": probs.tolist(),
            "sentiment": sentiment_category   # ✅ 긍정/부정/중립 추가
        }

    def analyze_audio(self, file_path: str):
        if self.audio_model is None:
            return {"error": "오디오 모델이 로드되지 않아 분석할 수 없습니다."}

        features = extract_features(file_path)
        x = torch.tensor(features, dtype=torch.float32)

        with torch.no_grad():
            logits = self.audio_model(x)

        label_idx = torch.argmax(logits, dim=1).item()
        return {
            "type": "audio",
            "label": label_map[label_idx]
        }

    def analyze_turn(self, turn: Turn):
        result = {
            "turn_index": turn.turn_index,
            "timestamp": turn.session_timestamp.isoformat() if turn.session_timestamp else None
        }
        if turn.customer_text:
            result["customer_emotion"] = self.analyze_text(turn.customer_text)
        if turn.agent_text:
            result["agent_emotion"] = self.analyze_text(turn.agent_text)
        return result

    def analyze(self, text=None, audio_path=None, turn: Turn = None):
        if text:
            return self.analyze_text(text)
        elif audio_path:
            return self.analyze_audio(audio_path)
        elif turn:
            return self.analyze_turn(turn)
        else:
            raise ValueError("텍스트, 오디오, 또는 Turn 객체 중 하나가 필요합니다.")

