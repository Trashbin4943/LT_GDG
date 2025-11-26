'''
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline # Pipeline 클래스 사용 권장 (3.1 이상)
# pyannote.core.Annotation 클래스를 가져옵니다.
# pyannote.core는 Pyannote 설치 시 함께 설치됩니다.
try:
    from pyannote.core import Annotation
except ImportError:
    # 이 예외는 pyannote.core가 설치되지 않았을 때만 발생해야 합니다.
    print("⚠️ [Import Error] 'pyannote.core' 모듈을 찾을 수 없습니다. pip install pyannote.core 를 실행하세요.")
    # 임시적으로 Annotation을 사용할 수 없도록 처리
    class Annotation:
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("pyannote.core.Annotation is not available.")

from dotenv import load_dotenv
import os
import json
from huggingface_hub import login
# torchaudio 대신 soundfile과 torch를 사용하여 오디오 로딩을 직접 처리합니다.
import soundfile as sf 
import torch
import numpy as np

# 환경 변수 로드
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# 🚀 변경됨: 최신 Pyannote 4.x 라이브러리에 맞는 3.1 모델 사용
REPO_ID = "pyannote/speaker-diarization-3.1"

# ⚠️ 디버깅 라인
print(f"[Debug] HF_TOKEN is loaded: {bool(HF_TOKEN)}")
print(f"[Debug] HF_TOKEN prefix: {HF_TOKEN[:8] if HF_TOKEN else 'None'}")

# Hugging Face 명시적 로그인
if HF_TOKEN:
    try:
        login(token=HF_TOKEN, add_to_git_credential=False)
        print("✅ [HF Auth] Hugging Face 토큰을 사용하여 명시적 로그인 성공.")
    except Exception as e:
        print(f"❌ [HF Auth] 명시적 로그인 실패. 원인: {e}")
else:
    print("❌ [HF Auth] HF_TOKEN 값이 없습니다.")

# Whisper 모델 초기화 (CPU 환경에서는 small 권장)
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

# 화자 분리 파이프라인 로드
def get_diarization_pipeline():
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN is not set in environment.")

    try:
        print(f"🔄 [Pyannote] 원격 리포지토리 ({REPO_ID})에서 파이프라인 로드 시도...")
        
        # Pyannote 3.1+ / 4.x 버전에서는 `use_auth_token` 인수가 제거되었습니다.
        pipeline = Pipeline.from_pretrained(REPO_ID)
        
        return pipeline
    except Exception as e:
        print(f"❌ Pyannote 파이프라인 로드 실패.")
        print(f"   원인: {e}")
        print("   👉 중요: 'pyannote/speaker-diarization-3.1' 및 의존성 모델들의 약관에 동의했는지 꼭 확인하세요!")
        raise e

def diarize_and_transcribe(audio_path, save_json=False, json_path="segments.json"):
    # 🎤 STT 실행
    print(f"🎤 [STT] Whisper 모델로 음성 인식 시작...")
    segments, info = whisper_model.transcribe(audio_path, language="ko")

    print(f"👥 [Diarization] 화자 분리 시작...")
    try:
        diarization_pipeline = get_diarization_pipeline()

        # 오디오 로드 및 텐서 변환
        waveform_numpy, sample_rate = sf.read(audio_path, dtype='float32')
        if waveform_numpy.ndim == 1:
            waveform_tensor = torch.from_numpy(waveform_numpy[np.newaxis, :])
        else:
            waveform_tensor = torch.from_numpy(waveform_numpy).T
        input_audio = {"waveform": waveform_tensor, "sample_rate": sample_rate}

        diarization = diarization_pipeline(input_audio)

    except Exception as e:
        print(f"❌ 화자 분리 실행 중 오류 발생: {e}")
        return []

    # 🚨 DEBUGGING
    print("\n=======================================================")
    print(f"DEBUG: Diarization 객체 타입: {type(diarization)}")
    print(f"DEBUG: Annotation 속성 타입: {type(diarization.annotation)}")
    print(f"DEBUG: .itertracks 존재 여부: {hasattr(diarization.annotation, 'itertracks')}")
    print("=======================================================\n")

    print(f"🔗 [Merging] STT 결과와 화자 정보 병합 시작...")

    results = []
    try:
        annotation = diarization.annotation  # 핵심 변경

        for segment, _, speaker_label in annotation.itertracks(yield_label=True):
            start_time = segment.start
            end_time = segment.end

            matched_texts = [
                seg.text for seg in segments
                if seg.start < end_time and seg.end > start_time
            ]
            text = " ".join(matched_texts).strip()

            results.append({
                "speaker": speaker_label,
                "start": start_time,
                "end": end_time,
                "text": text
            })

        print(f"✅ [Merging Success] 총 {len(results)}개의 세그먼트 생성 완료.")

    except Exception as e:
        print(f"❌ 화자 분리 결과 처리 중 최종 오류 발생: {e}")
        return []

    if save_json:
        print(f"💾 [Save] 결과를 {json_path}에 저장합니다.")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    return results

'''

from faster_whisper import WhisperModel
import json

# Whisper 모델 초기화 (CPU 환경에서는 small 권장)
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

def transcribe_with_timestamps(audio_path, save_json=False, json_path="segments.json"):
    # 🎤 Whisper STT 실행
    segments, info = whisper_model.transcribe(audio_path, language="ko")

    results = []
    for seg in segments:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip()
        })

    # 💾 JSON 저장 옵션
    if save_json:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    return results
