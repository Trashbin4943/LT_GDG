from django.db import models

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    class _DummyModule:  # 최소한의 placeholder
        def __getattr__(self, name):
            raise RuntimeError("PyTorch is not available in this deployment.")

    nn = _DummyModule()
from transformers import BertTokenizer, BertForSequenceClassification
from emotion_system.emotion.label_map import label_map

# 텍스트 감정 분석 모델 (KoBERT 기반)
class TextEmotionModel:
    def __init__(self, model_name="monologg/kobert"):
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(
            model_name, num_labels=len(label_map)
        )

    def predict(self, text: str):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        logits = outputs.logits
        label_idx = torch.argmax(logits, dim=1).item()
        return label_map[label_idx], logits


# 오디오 감정 분석 모델 (CNN-LSTM 앙상블)
class AudioEmotionModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(AudioEmotionModel, self).__init__()
        self.lstm = nn.LSTM(input_dim, 64, batch_first=True)
        self.fc_lstm = nn.Linear(64, num_classes)

        self.conv = nn.Conv1d(input_dim, 64, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc_cnn = nn.Linear(64, num_classes)

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        lstm_out = self.fc_lstm(hn.squeeze(0))

        cnn_out = self.conv(x.transpose(1, 2))
        cnn_out = self.pool(cnn_out).squeeze(-1)
        cnn_out = self.fc_cnn(cnn_out)

        return 0.6 * lstm_out + 0.4 * cnn_out

    def predict(self, features):
        with torch.no_grad():
            logits = self.forward(features)
            label_idx = torch.argmax(logits, dim=1).item()
        return label_map[label_idx], logits