from ninja import Router
from django.shortcuts import get_object_or_404
from ninja_jwt.authentication import JWTAuth
from audio_process.models import CallRecording, SpeakerSegment
from .emotion_system.emotion.text_emotion import classify_text_emotion

router = Router()
@router.post("/{session_id}/analyze", auth=JWTAuth())
def analyze_session_emotion(request, session_id: str):
    print(f"감정 분석 요청: {session_id}")
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    client_segments = SpeakerSegment.objects.filter(
        session_id=recording, 
        is_counselor=False
    )

    if not client_segments.exists():
        return {"status": "warning", "message": "분석할 고객 발화가 없습니다."}

    updated_count = 0
    update_list = []

    # 2. 분석 수행
    for seg in client_segments:
        if not seg.text or not seg.text.strip():
            continue
            
        try:
            # 텍스트 감정 분류 실행
            # (리턴값이 label, confidence_list 라고 가정)
            label, confidence = classify_text_emotion(seg.text)
            
            seg.emotion_label = label
            
            # 리스트로 넘어올 경우 에러 방지 (Max값 추출)
            if isinstance(confidence, list) or isinstance(confidence, tuple):
                seg.emotion_confidence = float(max(confidence))
            else:
                seg.emotion_confidence = float(confidence)
            
            update_list.append(seg)
            updated_count += 1
            
        except Exception as e:
            print(f"Segment {seg.id} 분석 에러: {e}")
            continue

    # 3. DB 저장
    if update_list:
        SpeakerSegment.objects.bulk_update(update_list, ['emotion_label', 'emotion_confidence'])

    return {
        "status": "success",
        "session_id": session_id,
        "analyzed_count": updated_count,
        "message": "감정 분석 완료"
    }