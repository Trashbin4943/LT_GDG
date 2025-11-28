import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 절대 경로로 수정
from emotion_analysis.emotion_system.emotion.label_map import label_map, sentiment_map
from emotion_analysis.emotion_system.features.extract_features import extract_features
from emotion_analysis.emotion_system.preprocessing.stt_preprocessor import Turn

import torch.nn as nn


class CNNEmotionModel(nn.Module):
    def __init__(self, num_classes=7):  # 체크포인트는 7 클래스
        super().__init__()
        self.conv1 = nn.Conv2d(1, 20, kernel_size=(3, 3), padding=1)
        self.conv2 = nn.Conv2d(20, 20, kernel_size=(3, 3), padding=1)
        self.conv3 = nn.Conv2d(20, 20, kernel_size=(3, 3), padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.relu = nn.ReLU()

        # fc 레이어는 첫 forward에서 자동 초기화
        self.fc1 = None
        self.fc2 = None
        self.fc3 = None
        self.num_classes = num_classes

    def _initialize_fc_layers(self, x):
        """첫 forward에서 fc 레이어 크기를 자동으로 설정"""
        flatten_dim = x.view(x.size(0), -1).size(1)
        self.fc1 = nn.Linear(flatten_dim, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, self.num_classes)

    def forward(self, x):
        x = x.unsqueeze(1)  # [batch, 1, height, width]
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.relu(self.conv3(x))
        x = self.pool(x)

        if self.fc1 is None:
            # 첫 forward에서 fc 레이어 초기화
            self._initialize_fc_layers(x)

        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)


# CNN 모델 라벨 (체크포인트 기준 7개)
cnn_label_map = {
    0: "분노",
    1: "슬픔",
    2: "기쁨",
    3: "중립",
    4: "불안",
    5: "혐오",
    6: "기타"
}

# 긍/부정/중립 매핑
sentiment_map_audio = {
    "긍정": ["기쁨"],
    "부정": ["분노", "슬픔", "불안", "혐오"],
    "중립": ["중립", "기타"]
}


class UnifiedEmotionAnalyzer:
    def __init__(
        self,
        text_model_name="rattyrat0/kote-multilabel-model",
        audio_weights_path=os.path.join(os.path.dirname(__file__), "model.pth")
    ):
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

        # 오디오 모델 로딩
        if os.path.exists(audio_weights_path):
            print("model.pth 파일 탐색 성공!")
            self.audio_model = CNNEmotionModel(num_classes=7)
            self.audio_model.load_state_dict(
                torch.load(audio_weights_path, map_location="cpu"),
                strict=False
            )
            self.audio_model.eval()
        else:
            print("⚠️ model.pth 파일이 없습니다. 오디오 분석 기능이 비활성화됩니다.")
            self.audio_model = None

    def analyze_text(self, text: str, threshold: float = 0.5):
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        ).to(self.device)

        with torch.no_grad():
            outputs = self.text_model(**inputs)

        probs = torch.sigmoid(outputs.logits).detach().cpu().numpy()[0]
        labels = [label_map[i] for i, p in enumerate(probs) if p >= threshold]

        sentiment_category = "중립"
        for category, emotions in sentiment_map.items():
            if any(label in emotions for label in labels):
                sentiment_category = category
                break

        return {
            "type": "text",
            "sentiment": sentiment_category
        }

    def analyze_audio(self, file_path: str):
        if self.audio_model is None:
            return {"error": "오디오 모델이 로드되지 않아 분석할 수 없습니다."}

        features = extract_features(file_path)
        x = torch.tensor(features, dtype=torch.float32)

        with torch.no_grad():
            logits = self.audio_model(x)

        label_idx = torch.argmax(logits, dim=1).item()
        raw_label = cnn_label_map[label_idx]

        # CNN 결과를 긍/부정/중립으로 변환
        sentiment_category = "중립"
        for category, emotions in sentiment_map_audio.items():
            if raw_label in emotions:
                sentiment_category = category
                break

        return {
            "type": "audio",
            "sentiment": sentiment_category,
            "raw_label": raw_label
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