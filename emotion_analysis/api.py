from ninja import Router, File
from django.shortcuts import get_object_or_404
from accounts.jwt_auth import JWTAuth
from audio_process.models import CallRecording, SpeakerSegment
from ninja.files import UploadedFile
import json

from .emotion_system.emotion.text_emotion import classify_text_emotion
from emotion_analysis.emotion_system.emotion.unified_emotion import UnifiedEmotionAnalyzer

router = Router()

@router.post("/{session_id}/analyze", auth=JWTAuth())
def analyze_session_emotion(request, session_id: str):
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    client_segments = recording.segments.filter(
        speaker_label='client',
        is_counselor=False)
    
    total_count = client_segments.count()
    print("고객 발화문 총 개수:", total_count)

    if not client_segments.exists():
        return {"status": "error", "message": "고객 발화 데이터가 없습니다."}
    
    updated_count = 0
    update_list = []

    print("고객 발화문 감정분석 시작 - 세션ID:", session_id)

    for seg in client_segments:
        if not seg.text or len(seg.text.strip()) == 0:
            print("빈 문장 건너뜀 - Segment ID:", seg.id)
            continue
        try:
            print("분석 중 - Segment ID:", seg.id, "텍스트:", seg.text[:20])
            label, confidence = classify_text_emotion(seg.text)
            seg.emotion_label = label
            seg.emotion_confidence = confidence
            update_list.append(seg)
            updated_count += 1

        except Exception as e:
            print(f"분석 실패: {e}")
            continue
    
    if update_list:
        SpeakerSegment.objects.bulk_update(update_list, ['emotion_label', 'emotion_confidence'])
    
    print("감정분석 완료 - 분석된 문장 수:", updated_count)

    return {
        "status": "success",
        "session_id": session_id,
        "analyzed_segments": updated_count,
        "message": f"총 {total_count}개 문장 중 {updated_count}개 문장 감정분석 완료."  
    }

@router.post("/analyze-json")
def analyze_json(request, file: UploadedFile = File(...)):
    analyzer = UnifiedEmotionAnalyzer()

    # 업로드된 JSON 파일 읽기
    data = json.load(file)

    results = []
    for seg in data.get("segments", []):
        text = seg.get("text", "")
        if text:
            emotion = analyzer.analyze_text(text)
            results.append({
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": text,
                "emotion": emotion
            })

    return {"status": "success", "results": results}

