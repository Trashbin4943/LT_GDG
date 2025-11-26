# 파이프라인 모드 문서

## 📋 개요

MainPipeline은 세 가지 작동 모드를 지원합니다. 각 모드는 다른 처리 전략을 사용하여 성능과 정확도의 균형을 조절합니다.

---

## 🔄 세 가지 모드

### 모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL
**빠른 대분류 → 조건부 소분류**

**처리 흐름**:
```
텍스트 입력
  ↓
Korcen으로 빠른 대분류 (우선순위 1)
  → 평균 1.30ms 처리
  ↓
조건부 모델 기반 소분류 (우선순위 2, 선택적)
  → 신뢰도 낮음 (< 0.7)
  → 특정 Label (PROFANITY) 추가 검증 필요
  → 문맥적 표현 의심 (CENSURE 등)
  → 세션 맥락 모호함
  ↓
최종 Label (Korcen 또는 모델)
```

**특징**:
- ✅ **가장 빠른 처리 속도**: 평균 0.46ms (테스트 결과)
- ✅ **리소스 효율적**: 모델을 선택적으로만 실행
- ✅ **실시간 처리 적합**: 빠른 응답 시간
- ⚠️ 문맥적 표현 감지 제한적 (모델이 선택적으로만 실행)

**적용 시나리오**:
- 실시간 처리 속도가 중요한 경우
- 대부분의 케이스가 명확한 패턴인 경우
- 리소스 효율성이 중요한 경우

---

### 모드 2: CLASSIFY_BOTH_ALWAYS
**대분류도 하되 여부와 상관없이 소분류**

**처리 흐름**:
```
텍스트 입력
  ↓
Korcen으로 대분류 수행
  → 평균 1.30ms 처리
  ↓
모델로 소분류 항상 실행
  → 평균 ~50-100ms 처리
  ↓
최종 Label 결정
  → 모델 결과 우선 사용
  → 모델이 없으면 Korcen 결과 사용
```

**특징**:
- ✅ **가장 정확한 분류**: 모델과 Korcen 모두 실행
- ✅ **문맥 고려**: 모델이 문맥을 고려하여 분류
- ❌ **처리 시간 증가**: 평균 0.54ms (테스트 결과, 모델 없을 때)
- ❌ **리소스 사용 증가**: 모델을 항상 실행

**적용 시나리오**:
- 정확도가 가장 중요한 경우
- 문맥적 표현 감지가 중요한 경우
- 처리 시간이 크게 중요하지 않은 경우

---

### 모드 3: DETAIL_FIRST_THEN_VERIFY
**소분류 후 대분류로 상황 검증**

**처리 흐름**:
```
텍스트 입력
  ↓
모델로 소분류 먼저 수행 (우선순위 1)
  → 평균 ~50-100ms 처리
  ↓
Korcen으로 대분류 검증 (우선순위 2)
  → 평균 1.30ms 처리
  ↓
결과 비교 및 최종 결정
  → 모델 결과와 Korcen 결과 일치: 신뢰도 증가
  → 모델 결과와 Korcen 결과 불일치: 신뢰도 감소
  ↓
최종 Label (모델 결과 사용, 신뢰도 조정)
```

**특징**:
- ✅ **검증 기반 분류**: 모델과 Korcen 결과 비교
- ✅ **신뢰도 조정**: 일치/불일치에 따라 신뢰도 조정
- ✅ **문맥 고려**: 모델이 문맥을 고려하여 분류
- ❌ **처리 시간 증가**: 평균 0.51ms (테스트 결과, 모델 없을 때)
- ❌ **리소스 사용 증가**: 모델을 항상 실행

**적용 시나리오**:
- 정확도와 검증이 모두 중요한 경우
- 모델 결과의 신뢰성을 확인하고 싶은 경우
- 처리 시간이 크게 중요하지 않은 경우

---

## 📊 모드별 비교표

| 항목 | 모드 1 (빠른 대분류) | 모드 2 (항상 소분류) | 모드 3 (검증) |
|------|---------------------|---------------------|--------------|
| **처리 속도** | ⭐⭐⭐ 매우 빠름 (0.46ms) | ⭐ 느림 (0.54ms) | ⭐ 느림 (0.51ms) |
| **정확도** | ⭐⭐ 높음 (대분류) | ⭐⭐⭐ 매우 높음 | ⭐⭐⭐ 매우 높음 |
| **리소스 사용** | ⭐⭐⭐ 낮음 | ⭐ 높음 | ⭐ 높음 |
| **문맥 고려** | ⭐ 제한적 | ⭐⭐⭐ 가능 | ⭐⭐⭐ 가능 |
| **검증 기능** | ❌ 없음 | ❌ 없음 | ✅ 있음 |
| **실시간 처리** | ✅ 적합 | ⚠️ 제한적 | ⚠️ 제한적 |

---

## 💻 사용 방법

### 기본 사용 (모드 1)

```python
from logic_classify_system.pipeline.main_pipeline import MainPipeline
from logic_classify_system.config.labels import PipelineMode

# 모드 1: 빠른 대분류 → 조건부 소분류 (기본값)
pipeline = MainPipeline(mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL)

result = pipeline.process("시발놈아", session_id="test_001")
```

### 모드 2 사용

```python
# 모드 2: 대분류도 하되 여부와 상관없이 소분류
pipeline = MainPipeline(mode=PipelineMode.CLASSIFY_BOTH_ALWAYS)

result = pipeline.process("시발놈아", session_id="test_001")
```

### 모드 3 사용

```python
# 모드 3: 소분류 후 대분류로 상황 검증
pipeline = MainPipeline(mode=PipelineMode.DETAIL_FIRST_THEN_VERIFY)

result = pipeline.process("시발놈아", session_id="test_001")
```

### AI-Hub 모델과 함께 사용

```python
# AI-Hub 모델과 함께 초기화
pipeline = MainPipeline(
    mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL,
    aihub_base_model_path="./model",
    aihub_model1_checkpoint="ckpt/class/checkpoint-56000",
    aihub_model2_checkpoint="ckpt/multi/checkpoint-XXXX"
)
```

---

## 🔍 모드별 처리 로직 상세

### 모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL

**코드 흐름**:
```python
if profanity_detected:
    # 1단계: Korcen으로 빠른 대분류
    korcen_label = _korcen_hint_to_label(profanity_category)
    
    # 2단계: 조건부 모델 실행
    if _should_use_model(korcen_label, korcen_confidence, text, session_context):
        model_label = special_label_filter.detect(text, session_context)
        if model_label:
            return model_label  # 모델 결과 사용
    
    # Korcen Label 사용
    return korcen_label
```

**조건부 모델 실행 조건**:
1. 신뢰도가 임계값 이하 (< 0.7)
2. 특정 Label (PROFANITY) 추가 검증 필요
3. 문맥적 표현 의심 (CENSURE 등)
4. 세션 맥락 모호함

### 모드 2: CLASSIFY_BOTH_ALWAYS

**코드 흐름**:
```python
if profanity_detected:
    # 1단계: Korcen으로 대분류
    korcen_label = _korcen_hint_to_label(profanity_category)
    
    # 2단계: 모델로 소분류 항상 실행
    model_label = special_label_filter.detect(text, session_context)
    
    if model_label:
        return model_label  # 모델 결과 우선 사용
    
    # 모델이 없으면 Korcen 결과 사용
    return korcen_label
```

### 모드 3: DETAIL_FIRST_THEN_VERIFY

**코드 흐름**:
```python
if profanity_detected:
    # 1단계: 모델로 소분류 먼저 수행
    model_label = special_label_filter.detect(text, session_context)
    
    # 2단계: Korcen으로 대분류 검증
    korcen_label = _korcen_hint_to_label(profanity_category)
    
    # 3단계: 결과 비교 및 최종 결정
    if model_label:
        if _labels_match(model_label, korcen_label):
            confidence += 0.1  # 일치: 신뢰도 증가
        else:
            confidence -= 0.1  # 불일치: 신뢰도 감소
        
        return model_label  # 모델 결과 사용 (신뢰도 조정)
    
    # 모델이 없으면 Korcen 결과 사용
    return korcen_label
```

---

## 📈 성능 비교 (테스트 결과)

### 처리 시간 비교

| 모드 | 평균 처리 시간 | 비고 |
|------|--------------|------|
| 모드 1 | 0.46ms | 가장 빠름 |
| 모드 2 | 0.54ms | 모델 없을 때 |
| 모드 3 | 0.51ms | 모델 없을 때 |

**참고**: 모델이 있을 때는 모드 2와 3의 처리 시간이 증가할 수 있습니다 (~50-100ms).

### 리소스 사용 비교

| 모드 | 모델 실행 빈도 | CPU 사용량 | 메모리 사용량 |
|------|--------------|-----------|--------------|
| 모드 1 | ~10-20% (추정) | 낮음 | 낮음 |
| 모드 2 | 100% | 높음 | 높음 |
| 모드 3 | 100% | 높음 | 높음 |

---

## 🎯 모드 선택 가이드

### 모드 1 (FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL) 선택 시

**적합한 경우**:
- ✅ 실시간 처리 속도가 중요한 경우
- ✅ 대부분의 케이스가 명확한 패턴인 경우
- ✅ 리소스 효율성이 중요한 경우
- ✅ 모바일/임베디드 환경

**부적합한 경우**:
- ❌ 문맥적 표현 감지가 중요한 경우
- ❌ 정확도가 가장 중요한 경우

### 모드 2 (CLASSIFY_BOTH_ALWAYS) 선택 시

**적합한 경우**:
- ✅ 정확도가 가장 중요한 경우
- ✅ 문맥적 표현 감지가 중요한 경우
- ✅ 처리 시간이 크게 중요하지 않은 경우
- ✅ 서버 환경 (충분한 리소스)

**부적합한 경우**:
- ❌ 실시간 처리 속도가 중요한 경우
- ❌ 리소스가 제한적인 경우

### 모드 3 (DETAIL_FIRST_THEN_VERIFY) 선택 시

**적합한 경우**:
- ✅ 정확도와 검증이 모두 중요한 경우
- ✅ 모델 결과의 신뢰성을 확인하고 싶은 경우
- ✅ 처리 시간이 크게 중요하지 않은 경우
- ✅ 서버 환경 (충분한 리소스)

**부적합한 경우**:
- ❌ 실시간 처리 속도가 중요한 경우
- ❌ 리소스가 제한적인 경우

---

## ⚙️ 구현 상세

### PipelineMode Enum

```python
class PipelineMode(Enum):
    FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL = "FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL"
    CLASSIFY_BOTH_ALWAYS = "CLASSIFY_BOTH_ALWAYS"
    DETAIL_FIRST_THEN_VERIFY = "DETAIL_FIRST_THEN_VERIFY"
```

### MainPipeline 초기화

```python
pipeline = MainPipeline(
    mode=PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL,
    aihub_base_model_path="./model",
    aihub_model1_checkpoint="ckpt/class/checkpoint-56000",
    aihub_model2_checkpoint="ckpt/multi/checkpoint-XXXX"
)
```

### IntentPredictor.predict() 메서드

```python
def predict(
    self,
    text: str,
    profanity_detected: bool,
    session_context: Optional[List[str]] = None,
    profanity_category: Optional[str] = None,
    profanity_confidence: float = 1.0,
    mode: PipelineMode = PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL
) -> ClassificationResult:
    # 모드에 따라 처리 방식 결정
    if mode == PipelineMode.FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL:
        return self._predict_fast_classify_then_conditional_detail(...)
    elif mode == PipelineMode.CLASSIFY_BOTH_ALWAYS:
        return self._predict_classify_both_always(...)
    elif mode == PipelineMode.DETAIL_FIRST_THEN_VERIFY:
        return self._predict_detail_first_then_verify(...)
```

---

## 📝 주의사항

### 1. 모델 의존성

- 모드 2와 3은 모델이 없으면 Korcen 결과만 사용
- 모델이 있을 때와 없을 때의 성능 차이가 큼

### 2. 처리 시간

- 모드 1: 항상 빠름 (평균 0.46ms)
- 모드 2, 3: 모델 없을 때는 빠름, 모델 있을 때는 느림 (~50-100ms)

### 3. 정확도

- 모드 1: 대분류 정확도 높음, 문맥적 표현 제한적
- 모드 2, 3: 문맥 고려 가능, 더 정확한 분류

---

## ✅ 테스트 결과

### 기본 기능 테스트

**모드 1**:
- ✅ 모든 테스트 케이스 통과
- ✅ Special Label 감지 정상
- ✅ Normal Label 분류 정상

**모드 2**:
- ✅ 모든 테스트 케이스 통과
- ✅ Special Label 감지 정상
- ✅ Normal Label 분류 정상

**모드 3**:
- ✅ 모든 테스트 케이스 통과
- ✅ Special Label 감지 정상
- ✅ Normal Label 분류 정상

### 성능 테스트

- 모드 1: 평균 0.46ms (가장 빠름)
- 모드 2: 평균 0.54ms
- 모드 3: 평균 0.51ms

---

## 📚 관련 문서

- `KORCEN_VS_MODEL_FRAMEWORK_COMPARISON.md`: 프레임워크 비교
- `KORCEN_PERFORMANCE_MONITORING_REPORT.md`: 성능 모니터링 리포트
- `IMPLEMENTATION_STATUS.md`: 구현 현황

