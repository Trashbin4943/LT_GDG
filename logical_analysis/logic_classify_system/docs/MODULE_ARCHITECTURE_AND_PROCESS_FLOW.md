# 모듈 아키텍처 및 프로세스 흐름

## 📋 목차

1. [개요](#개요)
2. [모듈 계층 구조](#모듈-계층-구조)
3. [데이터 흐름도](#데이터-흐름도)
4. [단계별 상세 프로세스](#단계별-상세-프로세스)
5. [모듈 간 의존성](#모듈-간-의존성)
6. [파이프라인 모드별 동작](#파이프라인-모드별-동작)

---

## 개요

**Logic Classify System**은 실시간 상담 시스템을 위한 텍스트 분류 파이프라인으로, 여러 모듈이 협력하여 고객 발화를 분석하고 분류합니다. 각 모듈은 **Single Responsibility Principle (SRP)**을 따르며, 명확한 책임과 인터페이스를 가지고 있습니다.

### 핵심 원칙

- **모듈 독립성**: 각 모듈은 독립적으로 테스트 가능
- **명확한 책임**: 각 모듈은 하나의 명확한 책임만 담당
- **데이터 중심 설계**: 표준화된 데이터 구조를 통한 모듈 간 통신
- **확장 가능성**: 새로운 분류기나 필터를 쉽게 추가 가능

---

## 모듈 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    MainPipeline (오케스트레이터)                │
│  - 전체 프로세스 조율                                          │
│  - 세션 관리                                                  │
│  - 파이프라인 모드 제어                                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ TextSplitter │   │ProfanityDet.│   │IntentPredict.│
│  (전처리)     │   │  (1차 필터)  │   │  (2차 분류)  │
└──────────────┘   └──────────────┘   └──────────────┘
                            │                   │
                            │                   ▼
                            │          ┌──────────────┐
                            │          │SpecialLabel │
                            │          │   Filter    │
                            │          └──────────────┘
                            │                   │
                            │                   ▼
                            │          ┌──────────────┐
                            │          │AIHubEthic   │
                            │          │   Model     │
                            │          └──────────────┘
                            │
                            ▼
                   ┌──────────────┐
                   │  LabelRouter │
                   │   (라우팅)    │
                   └──────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌──────────────┐              ┌──────────────┐
    │NormalLabel   │              │SpecialLabel  │
    │ Evaluator    │              │   Filter     │
    │  (평가)       │              │  (필터링)     │
    └──────────────┘              └──────────────┘
```

---

## 데이터 흐름도

### 전체 프로세스 흐름

```
[입력: STT 텍스트]
        │
        ▼
┌─────────────────┐
│  TextSplitter   │  → 문장 분할, 화자 구분
└─────────────────┘
        │
        ▼ (고객 문장 리스트)
┌─────────────────┐
│  MainPipeline   │
│  (각 문장 처리)  │
└─────────────────┘
        │
        ├─────────────────────────────────┐
        │                                 │
        ▼                                 ▼
┌─────────────────┐            ┌─────────────────┐
│ProfanityDetector│            │ SessionManager  │
│  (욕설 감지)     │            │  (맥락 관리)     │
└─────────────────┘            └─────────────────┘
        │                                 │
        │ ProfanityResult                │ session_context
        │ (is_profanity, category,       │
        │  confidence, method)          │
        │                                 │
        ▼                                 │
┌─────────────────┐                     │
│IntentPredictor   │ ←───────────────────┘
│  (의도 분류)     │
└─────────────────┘
        │
        │ (모드에 따라 분기)
        │
        ├─ FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL
        ├─ CLASSIFY_BOTH_ALWAYS
        └─ DETAIL_FIRST_THEN_VERIFY
        │
        ▼
┌─────────────────┐
│SpecialLabelFilter│ (Special Label 감지)
│  - AIHub Model   │
│  - Baseline Rules│
└─────────────────┘
        │
        │ ClassificationResult
        │ (label, label_type, confidence)
        │
        ▼
┌─────────────────┐
│  LabelRouter     │
│  (라우팅)        │
└─────────────────┘
        │
        ├─────────────────────┬─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│NormalLabel   │    │SpecialLabel  │    │   Unknown    │
│ Evaluator    │    │   Filter     │    │   (에러)     │
│              │    │              │    │              │
│ - 점수 계산   │    │ - 이벤트 생성 │    │              │
│ - 피드백 생성 │    │ - 알림 발송  │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │
        ▼                     ▼
[EvaluationResult]  [FilteringResult]
```

---

## 단계별 상세 프로세스

### 1단계: 전처리 (TextSplitter)

**모듈**: `preprocessing/text_splitter.py`

**책임**:
- STT 결과 텍스트를 문장 단위로 분할
- 화자 구분 (고객 vs 상담사)
- 고객 문장만 추출

**입력**:
```python
text: str  # "고객: 안녕하세요\n상담사: 네 안내드리겠습니다\n고객: 시발놈아"
```

**출력**:
```python
customer_sentences: List[str]  # ["안녕하세요", "시발놈아"]
agent_sentences: List[str]     # ["네 안내드리겠습니다"]
```

**처리 과정**:
1. 줄바꿈 기준으로 문장 분할
2. "고객:", "상담사:" 태그로 화자 구분
3. 고객 문장만 반환

---

### 2단계: 욕설 감지 (ProfanityDetector)

**모듈**: `profanity_filter/profanity_detector.py`

**책임**:
- 빠른 욕설 감지 (1차 필터링)
- Korcen 필터와 Baseline 규칙 조합
- 감지 힌트 제공 (PROFANITY_DETECTED, SEXUAL_DETECTED, etc.)

**입력**:
```python
sentence: str  # "시발놈아"
```

**처리 과정**:
1. **Korcen 필터 시도** (use_korcen=True인 경우)
   - 단어 단위 패턴 매칭
   - 4개 레벨 감지: `general`, `sexual`, `race`, `special`
   - 힌트 반환: `PROFANITY_DETECTED`, `SEXUAL_DETECTED`, `HATE_DETECTED`
   
2. **Baseline 규칙 폴백** (Korcen 실패 시)
   - 키워드 기반 감지
   - 직접 Special Label 반환: `VIOLENCE_THREAT`, `PROFANITY`, etc.

**출력**:
```python
ProfanityResult(
    is_profanity=True,
    category="PROFANITY_DETECTED",  # Korcen 힌트 또는 Baseline Label
    confidence=0.80,
    method="korcen"  # 또는 "baseline"
)
```

**내부 모듈**:
- `korcen_filter.py`: Korcen 필터 구현
- `baseline_rules.py`: Baseline 규칙 구현

---

### 3단계: 의도 분류 (IntentPredictor)

**모듈**: `intent_classifier/intent_predictor.py`

**책임**:
- Special Label 및 Normal Label 분류
- 파이프라인 모드에 따른 분기 처리
- SpecialLabelFilter에 위임하여 Special Label 감지

**입력**:
```python
text: str
profanity_detected: bool
session_context: List[str]
profanity_category: Optional[str]  # Korcen 힌트
profanity_confidence: float
mode: PipelineMode
```

**처리 과정 (모드별)**:

#### 모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL
```
1. Korcen 힌트 확인
   ├─ profanity_detected == True
   │  ├─ Korcen 힌트 → Special Label 변환
   │  └─ 조건 확인: 모델 사용 필요?
   │     ├─ Yes → SpecialLabelFilter.detect() (모델 기반)
   │     └─ No  → Korcen 힌트 기반 Label 반환
   │
   └─ profanity_detected == False
      └─ SpecialLabelFilter.detect() (모델/Baseline)
         ├─ Special Label 감지 → 반환
         └─ 미감지 → Normal Label 분류
```

#### 모드 2: CLASSIFY_BOTH_ALWAYS
```
1. SpecialLabelFilter.detect() (항상 실행)
   ├─ Special Label 감지 → 반환
   └─ 미감지
      ├─ profanity_detected == True
      │  └─ Korcen 힌트 → Special Label 변환
      └─ profanity_detected == False
         └─ Normal Label 분류
```

#### 모드 3: DETAIL_FIRST_THEN_VERIFY
```
1. SpecialLabelFilter.detect() (우선 실행)
   ├─ Special Label 감지
   │  ├─ profanity_detected == True
   │  │  └─ Korcen 힌트와 비교
   │  │     ├─ 일치 → 신뢰도 상향 조정
   │  │     └─ 불일치 → 신뢰도 하향 조정
   │  └─ profanity_detected == False
   │     └─ 모델 결과 반환
   │
   └─ 미감지
      ├─ profanity_detected == True
      │  └─ Korcen 힌트 → Special Label 변환
      └─ profanity_detected == False
         └─ Normal Label 분류
```

**출력**:
```python
ClassificationResult(
    label="PROFANITY",  # 또는 "INQUIRY", "VIOLENCE_THREAT", etc.
    label_type="SPECIAL",  # 또는 "NORMAL"
    confidence=0.80,
    text="시발놈아",
    timestamp=datetime.now()
)
```

**내부 모듈**:
- `baseline_rules.py`: Intent Baseline 규칙 (UNREASONABLE_DEMAND, REPETITION)
- `special_label_filter.py`: Special Label 필터 (위임)

---

### 4단계: Special Label 필터링 (SpecialLabelFilter)

**모듈**: `filtering/special_label_filter.py`

**책임**:
- Special Label 감지 (AI-Hub 모델 + Baseline 규칙)
- 이벤트 생성 및 알림 발송

**입력**:
```python
text: str
session_context: Optional[List[str]]
```

**처리 과정**:
1. **AI-Hub 모델 감지** (우선순위 1)
   - `AIHubSpecialLabelDetector.detect()`
   - 모델 1: 비도덕 여부 판단
   - 모델 2: 유형 분류 (VIOLENCE, SEXUAL, ABUSE, DISCRIMINATION)
   - 프로젝트 Special Label로 매핑
   
2. **Baseline 규칙 감지** (우선순위 2)
   - `IntentBaselineRules.detect_special_labels()`
   - UNREASONABLE_DEMAND, REPETITION 감지
   
3. **필터링 수행** (감지된 경우)
   - 심각도 계산
   - 이벤트 생성
   - 알림 발송

**출력**:
```python
SpecialLabelDetectionResult(
    label="PROFANITY",
    confidence=0.85,
    severity="HIGH",
    detection_method="aihub_model"
)
```

**내부 모듈**:
- `aihub_special_label_detector.py`: AI-Hub 모델 감지기
- `baseline_rules.py`: Filtering Baseline 규칙
- `event_generator.py`: 이벤트 생성
- `alert_system.py`: 알림 시스템

---

### 5단계: 라우팅 (LabelRouter)

**모듈**: `labeling/label_router.py`

**책임**:
- ClassificationResult의 label_type에 따라 적절한 처리 경로로 라우팅
- Normal Label → Evaluation
- Special Label → Filtering

**입력**:
```python
classification_result: ClassificationResult
session_context: Optional[List[str]]
agent_text: Optional[str]  # Normal Label 평가용
```

**처리 과정**:
```
ClassificationResult
        │
        ├─ label_type == "NORMAL"
        │  └─ NormalLabelEvaluator.evaluate()
        │     ├─ 점수 계산 (0-100)
        │     ├─ 기준별 점수 계산
        │     └─ 피드백 생성
        │
        ├─ label_type == "SPECIAL"
        │  └─ SpecialLabelFilter.filter()
        │     ├─ 심각도 확인
        │     ├─ 이벤트 생성
        │     └─ 알림 발송
        │
        └─ label_type == "UNKNOWN"
           └─ 에러 처리
```

**출력**:
```python
RouterResult(
    route_type="EVALUATION",  # 또는 "FILTERING", "UNKNOWN"
    result=EvaluationResult(...),  # 또는 FilteringResult(...)
    classification_result=ClassificationResult(...)
)
```

---

### 6단계: 평가/필터링

#### 6-1. Normal Label 평가 (NormalLabelEvaluator)

**모듈**: `evaluation/normal_label_evaluator.py`

**책임**:
- Normal Label의 품질 평가
- 점수 계산 및 피드백 생성

**평가 기준**:
- 적절성 (Appropriateness)
- 명확성 (Clarity)
- 맥락 일치 (Context Match)
- 응답 품질 (Response Quality)

**출력**:
```python
EvaluationResult(
    label="INQUIRY",
    score=85.0,
    criteria_scores={
        "appropriateness": 90.0,
        "clarity": 85.0,
        "context_match": 80.0,
        "response_quality": 85.0
    },
    feedback="고객의 문의가 명확하고 적절합니다."
)
```

#### 6-2. Special Label 필터링 (SpecialLabelFilter.filter)

**모듈**: `filtering/special_label_filter.py`

**책임**:
- Special Label의 심각도 확인
- 이벤트 생성 및 알림 발송

**출력**:
```python
FilteringResult(
    label="PROFANITY",
    severity="HIGH",
    action="ALERT",  # 또는 "BLOCK", "LOG"
    alert_level="HIGH",
    text="시발놈아",
    timestamp=datetime.now()
)
```

---

## 모듈 간 의존성

### 의존성 그래프

```
MainPipeline
    ├─ TextSplitter (독립)
    ├─ ProfanityDetector
    │   ├─ KorcenFilter (독립)
    │   └─ ProfanityBaselineRules (독립)
    ├─ IntentPredictor
    │   ├─ IntentBaselineRules (독립)
    │   └─ SpecialLabelFilter
    │       ├─ AIHubSpecialLabelDetector
    │       │   └─ AIHubEthicModel (독립)
    │       ├─ FilteringBaselineRules (독립)
    │       ├─ EventGenerator (독립)
    │       └─ AlertSystem (독립)
    └─ SessionManager (독립)

LabelRouter
    ├─ NormalLabelEvaluator (독립)
    └─ SpecialLabelFilter (위와 동일)
```

### 모듈 독립성

**완전 독립 모듈** (다른 모듈에 의존하지 않음):
- `TextSplitter`
- `KorcenFilter`
- `ProfanityBaselineRules`
- `IntentBaselineRules`
- `FilteringBaselineRules`
- `AIHubEthicModel`
- `EventGenerator`
- `AlertSystem`
- `SessionManager`
- `NormalLabelEvaluator`

**의존 모듈** (다른 모듈에 의존):
- `ProfanityDetector` → `KorcenFilter`, `ProfanityBaselineRules`
- `AIHubSpecialLabelDetector` → `AIHubEthicModel`
- `SpecialLabelFilter` → `AIHubSpecialLabelDetector`, `FilteringBaselineRules`, `EventGenerator`, `AlertSystem`
- `IntentPredictor` → `IntentBaselineRules`, `SpecialLabelFilter`
- `LabelRouter` → `NormalLabelEvaluator`, `SpecialLabelFilter`
- `MainPipeline` → 모든 모듈

---

## 파이프라인 모드별 동작

### 모드 1: FAST_CLASSIFY_THEN_CONDITIONAL_DETAIL

**목적**: 빠른 처리 속도, 리소스 효율적

**흐름**:
```
Korcen (빠른 대분류)
    ├─ 감지됨
    │  ├─ 신뢰도 높음 (≥0.7) → 즉시 반환
    │  └─ 신뢰도 낮음 (<0.7) → 모델 기반 소분류
    │     └─ SpecialLabelFilter.detect()
    │
    └─ 미감지
       └─ SpecialLabelFilter.detect()
          └─ Normal Label 분류
```

**특징**:
- Korcen 우선 사용
- 모델은 조건부 실행 (신뢰도 낮거나 모호한 경우)
- 가장 빠른 처리 속도

---

### 모드 2: CLASSIFY_BOTH_ALWAYS

**목적**: 최고 정확도

**흐름**:
```
SpecialLabelFilter.detect() (항상 실행)
    ├─ Special Label 감지 → 반환
    │
    └─ 미감지
       ├─ Korcen 감지 → 반환
       └─ Normal Label 분류
```

**특징**:
- Korcen과 모델 모두 실행
- 모델 결과 우선
- 가장 정확한 분류

---

### 모드 3: DETAIL_FIRST_THEN_VERIFY

**목적**: 검증 기반 정확도 향상

**흐름**:
```
SpecialLabelFilter.detect() (우선 실행)
    ├─ Special Label 감지
    │  ├─ Korcen도 감지됨
    │  │  ├─ 일치 → 신뢰도 상향
    │  │  └─ 불일치 → 신뢰도 하향
    │  └─ Korcen 미감지 → 모델 결과 반환
    │
    └─ 미감지
       ├─ Korcen 감지 → 반환
       └─ Normal Label 분류
```

**특징**:
- 모델 우선 실행
- Korcen으로 검증
- 일치/불일치에 따라 신뢰도 조정

---

## 데이터 구조 변환

### 프로세스별 데이터 변환

```
[입력]
str: "시발놈아"
        │
        ▼ [TextSplitter]
List[str]: ["시발놈아"]
        │
        ▼ [ProfanityDetector]
ProfanityResult(
    is_profanity=True,
    category="PROFANITY_DETECTED",
    confidence=0.80,
    method="korcen"
)
        │
        ▼ [IntentPredictor]
ClassificationResult(
    label="PROFANITY",
    label_type="SPECIAL",
    confidence=0.80,
    text="시발놈아"
)
        │
        ▼ [LabelRouter]
RouterResult(
    route_type="FILTERING",
    result=FilteringResult(...),
    classification_result=ClassificationResult(...)
)
```

---

## 세션 관리

**모듈**: `data/session_manager.py`

**책임**:
- 세션별 대화 맥락 저장
- 이전 발화 조회

**사용 위치**:
- `MainPipeline.process()`: 세션 맥락 조회 및 업데이트
- `IntentPredictor.predict()`: 세션 맥락을 통한 문맥 기반 분류

**데이터 구조**:
```python
session_context: List[str]  # ["안녕하세요", "시발놈아", ...]
```

---

## 에러 처리 및 폴백

### 폴백 전략

1. **Korcen 실패** → Baseline 규칙으로 폴백
2. **AI-Hub 모델 실패** → Baseline 규칙으로 폴백
3. **모델 미로드** → Mock 모드로 작동 (Baseline 규칙만 사용)
4. **분류 실패** → 기본값 반환 (INQUIRY, confidence=0.5)

### 에러 처리 위치

- `ProfanityDetector`: Korcen 실패 시 Baseline으로 폴백
- `AIHubEthicModel`: PyTorch 미설치 시 Mock 모드
- `SpecialLabelFilter`: 모델 실패 시 Baseline 규칙 사용
- `IntentPredictor`: 모든 분류 실패 시 기본값 반환

---

## 성능 최적화

### 캐싱 전략

- **AI-Hub 모델**: 모델 로드 후 메모리에 유지
- **Korcen 필터**: 초기화 시 패턴 로드
- **세션 맥락**: 메모리 기반 세션 관리

### 병렬 처리 가능 영역

- 여러 문장의 독립적 처리 (현재는 순차 처리)
- Korcen과 Baseline 규칙의 병렬 실행 (현재는 순차 실행)

---

## 확장 포인트

### 새로운 분류기 추가

1. `intent_classifier/` 폴더에 새 분류기 구현
2. `IntentPredictor`에 통합
3. 모드별 로직에 추가

### 새로운 필터 추가

1. `filtering/` 폴더에 새 필터 구현
2. `SpecialLabelFilter`에 통합
3. 우선순위 설정

### 새로운 평가 기준 추가

1. `evaluation/normal_label_evaluator.py`에 새 기준 추가
2. 점수 계산 로직 업데이트

---

## 참고 문서

- [README.md](./README.md): 프로젝트 개요 및 빠른 시작
- [LABELING_SYSTEM_DESIGN.md](./LABELING_SYSTEM_DESIGN.md): 라벨링 시스템 설계
- [PIPELINE_MODES_DOCUMENTATION.md](./PIPELINE_MODES_DOCUMENTATION.md): 파이프라인 모드 상세 설명
- [AIHUB_MODEL_INTEGRATION_ANALYSIS.md](./AIHUB_MODEL_INTEGRATION_ANALYSIS.md): AI-Hub 모델 통합 분석
- [IMPLEMENTATION_FILE_STRUCTURE.md](./IMPLEMENTATION_FILE_STRUCTURE.md): 파일 구조 상세

---

**작성일**: 2024년
**최종 수정일**: 2024년
**버전**: 1.0

