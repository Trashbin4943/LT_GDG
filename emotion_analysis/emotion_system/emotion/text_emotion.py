"""
KoBERT 기반 텍스트 감정 분석 (Hugging Face Hub 버전)
발화 텍스트를 입력받아 감정 라벨을 출력합니다.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .label_map import label_map

_tokenizer = None
_model = None
_device = "cuda" if torch.cuda.is_available() else "cpu"

def load_text_model():
    global _tokenizer, _model, _device
    
    if _model is None:
        print("⏳ [AI] Hugging Face 텍스트 감정 모델 로딩 중...")
        
        # Hugging Face Hub에서 업로드한 모델 불러오기
        model_name = "rattyrat0/kote-multilabel-model"
        _tokenizer = AutoTokenizer.from_pretrained("monologg/kobert", trust_remote_code=True)  # KoBERT 토크나이저
        _model = AutoModelForSequenceClassification.from_pretrained(model_name)

        _model.to(_device)
        _model.eval()
        print("✅ Hugging Face 모델 로딩 완료!")

def classify_text_emotion(text: str, threshold: float = 0.5):
    """
    텍스트 감정 분석 실행
    Args:
        text (str): 입력 문장
        threshold (float): 감정 라벨 선택 기준 확률 (기본 0.5)
    Returns:
        (predicted_labels, probs): 예측된 감정 라벨 리스트와 전체 확률 벡터
    """
    global _tokenizer, _model, _device

    if _model is None or _tokenizer is None:
        load_text_model()

    try:
        inputs = _tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            padding=True, 
            max_length=128
        ).to(_device)

        with torch.no_grad():
            outputs = _model(**inputs)
            
        # 멀티라벨 분류 → sigmoid 사용
        probs = torch.sigmoid(outputs.logits).detach().cpu().numpy()[0]
        predicted_labels = [label_map[i] for i, p in enumerate(probs) if p >= threshold]
        
        return predicted_labels, probs.tolist()
    
    except Exception as e:
        print(f"감정 분류 실패: {e}")
        raise e