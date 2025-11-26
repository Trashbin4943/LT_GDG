import os
from pyannote.audio import Pipeline
from dotenv import load_dotenv
from huggingface_hub import login
import soundfile as sf 
import torch
import numpy as np

# --- 1. 환경 설정 ---
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "pyannote/speaker-diarization-3.1"

# ⚠️ 여기에 테스트할 오디오 파일 경로를 입력하세요!
# 이 경로는 스크립트를 실행하는 환경에서 접근 가능해야 합니다.
AUDIO_PATH = "C:\Users\Administrator\Videos\Desktop\Trim_sample_1.mp3" 
# AUDIO_PATH = "/path/to/your/test_call.wav"

# Hugging Face 로그인
if not HF_TOKEN:
    print("❌ HF_TOKEN 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    exit()

try:
    login(token=HF_TOKEN, add_to_git_credential=False)
    print("✅ [HF Auth] Hugging Face 토큰 로그인 성공.")
except Exception as e:
    print(f"❌ [HF Auth] 로그인 실패. 원인: {e}")
    exit()

# --- 2. Pyannote 파이프라인 실행 ---
print(f"\n🔄 [Pyannote] 파이프라인 로드 및 실행 시작...")

if not os.path.exists(AUDIO_PATH):
    print(f"❌ 오디오 파일 경로를 찾을 수 없습니다: {AUDIO_PATH}")
    print("   👉 `AUDIO_PATH` 변수를 올바른 경로로 수정해주세요.")
    exit()

try:
    pipeline = Pipeline.from_pretrained(REPO_ID)

    # 오디오 로드 및 Pyannote 입력 형식으로 변환
    waveform_numpy, sample_rate = sf.read(AUDIO_PATH, dtype='float32')
    if waveform_numpy.ndim == 1:
        waveform_tensor = torch.from_numpy(waveform_numpy[np.newaxis, :])
    else:
        waveform_tensor = torch.from_numpy(waveform_numpy).T 
    
    input_audio = {
        "waveform": waveform_tensor,
        "sample_rate": sample_rate
    }

    diarization = pipeline(input_audio)
    
    print("✅ [Diarization] 화자 분리 성공.")

except Exception as e:
    print(f"❌ [Diarization Error] 파이프라인 실행 중 오류 발생: {e}")
    print("   👉 Pyannote 라이브러리 재설치(.sh 파일 참고) 또는 Pyannote/speaker-diarization-3.1 모델 약관 동의가 필요할 수 있습니다.")
    exit()

# --- 3. DiarizeOutput 객체 분석 ---
print("\n--- 🔎 DiarizeOutput 객체 분석 시작 ---")
print(f"객체 타입: {type(diarization)}")
print(f"객체 __str__:\n{diarization}")

# 3-1. 표준 속성 및 메서드 확인
attributes = ['itertracks', 'segments', 'for_json', '__iter__']
for attr in attributes:
    has_attr = hasattr(diarization, attr)
    print(f" - .{attr}: {'✅ 존재' if has_attr else '❌ 없음'}")

# 3-2. `.itertracks()` 테스트
if hasattr(diarization, 'itertracks'):
    try:
        print("\n--- ✅ .itertracks(yield_label=True) 테스트 ---")
        for i, (segment, _, speaker_label) in enumerate(diarization.itertracks(yield_label=True)):
            if i < 3: # 처음 3개만 출력
                print(f"  [Track {i}] Speaker: {speaker_label}, Start: {segment.start:.2f}, End: {segment.end:.2f}")
        print(f"  총 {i+1}개 트랙 확인 완료.")
    except Exception as e:
        print(f"  ❌ .itertracks() 호출 실패. 오류: {e}")

# 3-3. `.for_json()` 테스트
if hasattr(diarization, 'for_json'):
    try:
        print("\n--- ✅ .for_json() 테스트 ---")
        json_output = diarization.for_json()
        print(f"  결과 타입: {type(json_output)}")
        if isinstance(json_output, list) and len(json_output) > 0:
            print(f"  첫 번째 요소: {json_output[0]}")
        else:
            print("  JSON 출력이 비어 있거나 예상과 다름.")
    except Exception as e:
        print(f"  ❌ .for_json() 호출 실패. 오류: {e}")

# 3-4. .segments 테스트 (구버전 방식)
if hasattr(diarization, 'segments'):
    try:
        print("\n--- ✅ .segments 테스트 ---")
        segment_list = list(diarization.segments())
        print(f"  세그먼트 개수: {len(segment_list)}")
    except Exception as e:
        print(f"  ❌ .segments 호출 실패. 오류: {e}")

# 3-5. Annotation() 변환 테스트 (speaker_split.py의 현재 로직)
try:
    from pyannote.core import Annotation
    print("\n--- ✅ Annotation() 변환 테스트 ---")
    annotation_output = Annotation(diarization)
    print(f"  변환 성공. 변환된 객체 타입: {type(annotation_output)}")
    
    print("\n--- ✅ Annotation.itertracks() 테스트 ---")
    for i, (segment, _, speaker_label) in enumerate(annotation_output.itertracks(yield_label=True)):
        if i < 3:
            print(f"  [Annotation Track {i}] Speaker: {speaker_label}, Start: {segment.start:.2f}, End: {segment.end:.2f}")
    print(f"  총 {i+1}개 트랙 확인 완료.")

except ImportError:
    print("\n⚠️ pyannote.core.Annotation을 찾을 수 없습니다. 설치가 필요합니다.")
except Exception as e:
    print(f"  ❌ Annotation() 변환 후 .itertracks() 호출 실패. 오류: {e}")