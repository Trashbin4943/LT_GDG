# 파이프라인 모듈 개요

## 빠른 시작

### 기본 사용법

```python
from logical_analysis.logic_classify_system.pipeline import MainPipeline

# 파이프라인 초기화
pipeline = MainPipeline(
    intensity_model_path="./models/intensity_model",
    ternary_model_path="./models/ternary_model",
    use_two_stage_session=True,
    aihub_base_path="./models/aihub/base_model"
)

# 실행
result = pipeline.process(text="손님 대화", session_id="session_123")
```

## 세 단계 세션 구조

1. **BaselineValidationSession**: Baseline keyword + AI hub 모델 검증
2. **IntensityValidationSession**: Special label만 intensity 검증
3. **FinalScoreCalculationSession**: 최종 점수 계산 및 조정

## 주요 파일

- `main_pipeline.py`: 메인 파이프라인 (세션 오케스트레이션)
- `baseline_validation_session.py`: 첫 번째 세션
- `intensity_validation_session.py`: 두 번째 세션
- `final_score_calculation_session.py`: 세 번째 세션
- `session_utils.py`: 공통 유틸리티 함수

## 상세 문서

자세한 내용은 [PIPELINE_REDESIGN_DOCUMENTATION.md](./PIPELINE_REDESIGN_DOCUMENTATION.md) 참조

