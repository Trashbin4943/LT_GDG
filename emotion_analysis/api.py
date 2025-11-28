import os
import tempfile
from ninja import Router
from django.shortcuts import get_object_or_404
from ninja_jwt.authentication import JWTAuth

from audio_process.models import CallRecording, SpeakerSegment
from pydub import AudioSegment
from .emotion_system.emotion.unified_emotion import UnifiedEmotionAnalyzer

router = Router()

@router.post("/{session_id}/analyze", auth=JWTAuth())
def analyze_session_emotion(request, session_id: str):
    print(f"[감정 분석 요청(Audio+Text)] Session: {session_id}")
    
    # 1. 모델 초기화
    try:
        analyzer = UnifiedEmotionAnalyzer()
    except Exception as e:
        return 500, {"status": "error", "message": f"모델 로딩 실패: {str(e)}"}

    recording = get_object_or_404(CallRecording, session_id=session_id)

    if not recording.audio_file:
        return {"status": "error", "message": "원본 오디오 파일을 찾을 수 없습니다."}
    
    # 전체 오디오 로드 (한 번만 로드해서 메모리 절약)
    try:
        recording.audio_file.open()
        full_audio = AudioSegment.from_file(recording.audio_file)

    except Exception as e:
        return {"status": "error", "message": f"오디오 파일 로드 실패: {str(e)}"}

    target_segments = SpeakerSegment.objects.filter(
        session_id=recording, 
        is_counselor=False 
    )

    if not target_segments.exists():
        return {"status": "warning", "message": "분석할 고객 발화가 없습니다."}

    updated_count = 0
    update_list = []

    # 3. 구간별 분석 (Loop)
    for seg in target_segments:
        text_sentiment = "중립"
        if seg.text and seg.text.strip():
            try:
                res_text = analyzer.analyze(text=seg.text)
                text_sentiment = res_text.get('sentiment', '중립')
            except:
                pass

        audio_sentiment = None
        
        if seg.start_time is not None and seg.end_time is not None:
            try:
                start_ms = int(seg.start_time * 1000)
                end_ms = int(seg.end_time * 1000)
                
                if end_ms - start_ms > 500:
                    # (1) 오디오 자르기
                    chunk = full_audio[start_ms:end_ms]
                    
                    # (2) 임시 파일로 저장 (Analyzer가 파일 경로를 요구하므로)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        chunk.export(tmp_file.name, format="wav")
                        tmp_path = tmp_file.name
                    
                    # (3) 오디오 감정 분석 실행
                    # analyze(audio_path=...) 호출
                    res_audio = analyzer.analyze(audio_path=tmp_path)
                    audio_sentiment = res_audio.get('sentiment')
                    
                    # (4) 임시 파일 삭제
                    os.remove(tmp_path)
            except Exception as e:
                print(f"Seg {seg.id} 오디오 분석 실패: {e}")

        # 4. 최종 결과 결정 (앙상블 or 우선순위)
        # 정책 결정: 오디오 감정이 나오면 그걸 쓰고, 없으면 텍스트 감정을 쓴다.
        # (혹은 둘 다 저장할 수도 있음. 여기선 하나로 합침)
        final_label = audio_sentiment if audio_sentiment else text_sentiment
        
        # DB 업데이트
        seg.emotion_label = final_label
        seg.emotion_confidence = 0.0 # 확률값은 현재 모델 구조상 0.0
        
        update_list.append(seg)
        updated_count += 1

    # 5. 저장
    if update_list:
        SpeakerSegment.objects.bulk_update(update_list, ['emotion_label', 'emotion_confidence'])
        print(f"[분석 완료] 총 {updated_count}건 (Audio/Text 통합) 업데이트됨")

    return {
        "status": "success",
        "analyzed_count": updated_count,
        "message": "오디오+텍스트 감정 분석 완료"
    }