import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from emotion_system.emotion.label_map import label_map
from emotion_system.features.extract_features import extract_features
from emotion_system.emotion.audio_emotion import SimpleLSTM
from emotion_system.preprocessing.stt_preprocessor import Turn

class UnifiedEmotionAnalyzer:
    def __init__(self, text_model_name="rattyrat0/kote-multilabel-model", audio_weights_path="./audio_emotion_model.pth"):
        self.tokenizer = AutoTokenizer.from_pretrained("monologg/kobert")
        self.text_model = AutoModelForSequenceClassification.from_pretrained(text_model_name)
        self.text_model.eval()

        self.audio_model = SimpleLSTM(input_dim=23, num_classes=len(label_map))
        self.audio_model.load_state_dict(torch.load(audio_weights_path, map_location="cpu"))
        self.audio_model.eval()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.text_model.to(self.device)

    def analyze_text(self, text: str, threshold: float = 0.5):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128).to(self.device)
        with torch.no_grad():
            outputs = self.text_model(**inputs)
        probs = torch.sigmoid(outputs.logits).detach().cpu().numpy()[0]
        labels = [label_map[i] for i, p in enumerate(probs) if p >= threshold]
        return {"type": "text", "labels": labels, "probs": probs.tolist()}

    def analyze_audio(self, file_path: str):
        features = extract_features(file_path)
        x = torch.tensor(features, dtype=torch.float32)
        with torch.no_grad():
            logits = self.audio_model(x)
        label_idx = torch.argmax(logits, dim=1).item()
        return {"type": "audio", "label": label_map[label_idx]}

    def analyze_turn(self, turn: Turn):
        result = {"turn_index": turn.turn_index, "timestamp": turn.session_timestamp.isoformat() if turn.session_timestamp else None}
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
