# 모델 파일 복사 스크립트
# 추론에 필요한 파일만 선별하여 프로젝트 내부로 복사

param(
    [string]$SourceCheckpoints = "C:\Users\SAMSUNG\Documents\checkpoints",
    [string]$SourceAIModel = "C:\Users\SAMSUNG\Documents\1.AI 모델 소스코드",
    [string]$TargetBase = "logical_analysis\logic_classify_system\models"
)

Write-Host "=== 모델 파일 복사 스크립트 ===" -ForegroundColor Cyan
Write-Host ""

# 1. Intensity Regression Model 복사
Write-Host "[1/3] Intensity Regression Model 복사 중..." -ForegroundColor Yellow
$intensitySource = Join-Path $SourceCheckpoints "intensity_regression\intensity_model"
$intensityTarget = Join-Path $TargetBase "checkpoints\intensity_regression\intensity_model"

if (Test-Path $intensitySource) {
    # 디렉토리 생성
    New-Item -ItemType Directory -Force -Path $intensityTarget | Out-Null
    
    # 필수 파일 복사
    $intensityFiles = @(
        "config.json",
        "model.safetensors",
        "tokenizer_config.json",
        "tokenizer_78b3253a26.model",
        "vocab.txt",
        "tokenization_kobert.py"
    )
    
    foreach ($file in $intensityFiles) {
        $sourceFile = Join-Path $intensitySource $file
        $targetFile = Join-Path $intensityTarget $file
        
        if (Test-Path $sourceFile) {
            Copy-Item -Path $sourceFile -Destination $targetFile -Force
            Write-Host "  ✓ $file 복사 완료" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file 없음" -ForegroundColor Red
        }
    }
    Write-Host "  Intensity Regression Model 복사 완료" -ForegroundColor Green
} else {
    Write-Host "  ✗ 소스 경로를 찾을 수 없습니다: $intensitySource" -ForegroundColor Red
}

Write-Host ""

# 2. Ternary Classification Model 복사
Write-Host "[2/3] Ternary Classification Model 복사 중..." -ForegroundColor Yellow
$ternarySource = Join-Path $SourceCheckpoints "ternary_classification\ternary_model"
$ternaryTarget = Join-Path $TargetBase "checkpoints\ternary_classification\ternary_model"

if (Test-Path $ternarySource) {
    # 디렉토리 생성
    New-Item -ItemType Directory -Force -Path $ternaryTarget | Out-Null
    
    # 필수 파일 복사
    $ternaryFiles = @(
        "config.json",
        "model.safetensors",
        "tokenizer_config.json",
        "tokenizer_78b3253a26.model",
        "vocab.txt",
        "tokenization_kobert.py"
    )
    
    foreach ($file in $ternaryFiles) {
        $sourceFile = Join-Path $ternarySource $file
        $targetFile = Join-Path $ternaryTarget $file
        
        if (Test-Path $sourceFile) {
            Copy-Item -Path $sourceFile -Destination $targetFile -Force
            Write-Host "  ✓ $file 복사 완료" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file 없음" -ForegroundColor Red
        }
    }
    Write-Host "  Ternary Classification Model 복사 완료" -ForegroundColor Green
} else {
    Write-Host "  ✗ 소스 경로를 찾을 수 없습니다: $ternarySource" -ForegroundColor Red
}

Write-Host ""

# 3. AIHub Base Model 복사 (pytorch_model.bin 제외)
Write-Host "[3/3] AIHub Base Model 복사 중..." -ForegroundColor Yellow
$aihubSource = Join-Path $SourceAIModel "model"
$aihubTarget = Join-Path $TargetBase "aihub\base_model"

if (Test-Path $aihubSource) {
    # 디렉토리 생성
    New-Item -ItemType Directory -Force -Path $aihubTarget | Out-Null
    
    # 필수 파일 복사 (pytorch_model.bin 제외)
    $aihubFiles = @(
        "config.json",
        "tokenizer_config.json",
        "vocab.txt"
    )
    
    foreach ($file in $aihubFiles) {
        $sourceFile = Join-Path $aihubSource $file
        $targetFile = Join-Path $aihubTarget $file
        
        if (Test-Path $sourceFile) {
            Copy-Item -Path $sourceFile -Destination $targetFile -Force
            Write-Host "  ✓ $file 복사 완료" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $file 없음" -ForegroundColor Red
        }
    }
    Write-Host "  AIHub Base Model 복사 완료 (pytorch_model.bin은 제외됨)" -ForegroundColor Green
} else {
    Write-Host "  ✗ 소스 경로를 찾을 수 없습니다: $aihubSource" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 복사 완료 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "1. 모델 파일들이 올바르게 복사되었는지 확인하세요"
Write-Host "2. 모델 로드 테스트를 실행하세요"
Write-Host "3. pytorch_model.bin은 수동으로 복사해야 합니다 (용량이 큼)"

