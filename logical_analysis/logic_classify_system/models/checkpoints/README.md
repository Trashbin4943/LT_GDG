# 모델 Checkpoints 디렉토리

이 디렉토리는 학습된 모델 파일들을 저장하는 곳입니다.

## 📁 디렉토리 구조

```
checkpoints/
├── intensity_regression/
│   └── intensity_model/
│       ├── config.json ✅ (Git 추적)
│       ├── model.safetensors ⚠️ (Gitignore, 용량 큼)
│       ├── tokenizer_config.json ✅ (Git 추적)
│       ├── tokenizer_78b3253a26.model ⚠️ (Gitignore, 용량 큼)
│       ├── vocab.txt ⚠️ (Gitignore, 용량 큼)
│       └── tokenization_kobert.py ✅ (Git 추적)
└── ternary_classification/
    └── ternary_model/
        ├── config.json ✅ (Git 추적)
        ├── model.safetensors ⚠️ (Gitignore, 용량 큼)
        ├── tokenizer_config.json ✅ (Git 추적)
        ├── tokenizer_78b3253a26.model ⚠️ (Gitignore, 용량 큼)
        ├── vocab.txt ⚠️ (Gitignore, 용량 큼)
        └── tokenization_kobert.py ✅ (Git 추적)
```

## 📦 모델 파일 설치

### 자동 설치 (스크립트 사용)

```powershell
# 프로젝트 루트에서 실행
.\scripts\copy_model_files.ps1
```

### 수동 설치

각 모델 디렉토리에 다음 파일들을 복사하세요:

#### Intensity Regression Model
- `config.json` ✅
- `model.safetensors` ⚠️
- `tokenizer_config.json` ✅
- `tokenizer_78b3253a26.model` ⚠️
- `vocab.txt` ⚠️
- `tokenization_kobert.py` ✅

#### Ternary Classification Model
- `config.json` ✅
- `model.safetensors` ⚠️
- `tokenizer_config.json` ✅
- `tokenizer_78b3253a26.model` ⚠️
- `vocab.txt` ⚠️
- `tokenization_kobert.py` ✅

## ⚠️ 주의사항

1. **용량이 큰 파일들**은 Git에서 추적되지 않습니다:
   - `*.safetensors` (모델 가중치)
   - `*.model` (토크나이저 모델)
   - `vocab.txt` (어휘 사전)

2. **작은 설정 파일들**은 Git에서 추적됩니다:
   - `config.json`
   - `tokenizer_config.json`
   - `tokenization_kobert.py`

3. **학습 관련 파일들**은 포함하지 않습니다:
   - `optimizer.pt`
   - `rng_state.pth`
   - `scaler.pt`
   - `scheduler.pt`
   - `trainer_state.json`
   - `training_args.bin`

## 🔍 모델 파일 확인

모델 파일이 올바르게 설치되었는지 확인:

```python
from logical_analysis.logic_classify_system.config.model_paths import (
    get_intensity_model_path,
    get_ternary_model_path
)

intensity_path = get_intensity_model_path()
ternary_path = get_ternary_model_path()

print(f"Intensity Model: {intensity_path}")
print(f"Ternary Model: {ternary_path}")
```

## 📚 관련 문서

- `모델_파일_통합_계획.md`: 통합 계획 및 상세 정보
- `모델_설치_및_설정_가이드.md`: 모델 설치 가이드

