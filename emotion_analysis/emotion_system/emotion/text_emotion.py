'''
KoBERT 기반 텍스트 감정 분석
발화 텍스트를 입력받아 감정 라벨을 출력합니다.
'''

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import BertTokenizer, BertForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    BertTokenizer = None
    BertForSequenceClassification = None
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ [Import Warning] transformers not available. Text emotion classification disabled.")

from .label_map import label_map
import os

_tokenizer = None
_model = None
_device = "cuda" if (torch is not None and torch.cuda.is_available()) else "cpu"

def load_text_model():
    global _tokenizer, _model, _device
    
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("transformers library is not installed. Cannot load text emotion model.")
    
    if _model is None:
        print("⏳ [AI] KoBERT 텍스트 감정 모델 로딩 중...")
        
        model_name = "monologg/kobert"
        _tokenizer = BertTokenizer.from_pretrained(model_name)
        _model = BertForSequenceClassification.from_pretrained(
            model_name, 
            num_labels=len(label_map)
        )

        weights_path = "./emotion_analysis/emotion_system/emotion/kobert_emotion_model.pth"

        if os.path.exists(weights_path):
            try:
                state_dict = torch.load(weights_path, map_location=_device)
                _model.load_state_dict(state_dict)
            except Exception as e:
                print(f"모델 로드 실패: {e}")
                raise e
        else:
            raise FileNotFoundError(f"모델 가중치 파일을 찾을 수 없습니다: {weights_path}")

        _model.to(_device)
        _model.eval()
        print("✅ KoBERT 로딩 완료!")
            
        

# def classify_text_emotion(text):
#     tokenizer = BertTokenizer.from_pretrained("monologg/kobert")
#     model = BertForSequenceClassification.from_pretrained("monologg/kobert", num_labels=len(label_map))
#     inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
#     outputs = model(**inputs)
#     label = torch.argmax(outputs.logits, dim=1).item()
#     return label_map[label]

def classify_text_emotion(text):
    """
    텍스트 감정 분석 함수
    transformers가 없으면 기본 중립 감정 반환
    """
    global _tokenizer, _model, _device

    if not TRANSFORMERS_AVAILABLE:
        print("⚠️ [Text Emotion] transformers not available. Returning default neutral emotion.")
        return "neutral", 0.0

    if _model is None or _tokenizer is None:
        try:
            load_text_model()
        except ImportError as e:
            print(f"⚠️ [Text Emotion] Model loading failed: {e}")
            return "neutral", 0.0

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
            
        probs = torch.softmax(outputs.logits, dim=1)
        top_prob, top_label_idx = torch.max(probs, dim=1)

        label_idx = top_label_idx.item()
        confidence = top_prob.item()

        label_str = label_map.get(label_idx, "unknown")
        
        return label_str, confidence
    
    except Exception as e:
        print(f"감정 분류 실패: {e}")
        return "neutral", 0.0
