from ninja import Router, File, UploadedFile
from django.shortcuts import get_object_or_404
from .models import CallRecording, SpeakerSegment
from accounts.jwt_auth import JWTAuth
from typing import List
from .schemas import (
    RecordingListSchema, 
    RecordingDetailSchema, 
    RecordingUploadResponse,
    SpeakerSegmentSchema, 
    SpeakerUpdateSchema
)
from .audio_system.diarization.speaker_split import transcribe_with_timestamps
from .audio_system.utils.audio_utils import download_and_convert_to_wav, cleanup_temp_file

router = Router()

@router.post("/upload", auth=JWTAuth(), response=RecordingUploadResponse)
def upload_and_process(request, file: UploadedFile = File(...)):
    print("요청자: ", request.user)
    
    # 1. CallRecording 생성
    recording = CallRecording.objects.create(
        audio_file=file,
        file_name=file.name,
        uploader=request.user
    )
    
    local_wav_path = None
    try:
        # 2. S3 다운로드 및 변환
        local_wav_path = download_and_convert_to_wav(recording.audio_file)
        print(f"분석 시작: {local_wav_path}")
        
        # 3. Whisper STT 실행
        segments_data = transcribe_with_timestamps(local_wav_path)
        
        # 4. SpeakerSegment 객체 생성 (bulk_create용)
        objs = [
            SpeakerSegment(
                session_id=recording, 
                turn_index=idx,       
                speaker_label="unknown",
                start_time=item['start'],
                end_time=item['end'],
                text=item['text']
            ) for idx, item in enumerate(segments_data)
        ]
        
        # DB 저장
        SpeakerSegment.objects.bulk_create(objs)
        
        # 5. CallRecording 업데이트
        recording.processed = True
        recording.duration = segments_data[-1]['end'] if segments_data else 0.0
        recording.save()
        
        # 6. 응답 반환 (id 포함)
        return {
            "status": "success",
            "id": recording.id,
            "session_id": str(recording.session_id),
            "message": "업로드 및 분석이 완료되었습니다."
        }

    except Exception as e:
        print(f"Error: {e}")
        raise e

    finally:
        cleanup_temp_file(local_wav_path)


@router.get("/list", response=List[RecordingListSchema], auth=JWTAuth())
def get_recording_list(request):
    recordings = CallRecording.objects.filter(
        uploader=request.user
    ).order_by('-created_at')
    return recordings


@router.get('/{session_id}', response=RecordingDetailSchema, auth=JWTAuth())
def get_recording_detail(request, session_id: str):
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    segments = recording.segments.all().order_by('turn_index')
    
    result_segments = []
    
    for seg in segments:
        seg_data = {
            "id": seg.id,
            "speaker_label": seg.speaker_label,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text,
            "emotion_label": seg.emotion_label,
            "emotion_confidence": seg.emotion_confidence,
            
            "logical_label": None,
            "logical_type": None,
            "risk_score": 0.0,
            "is_profanity": False,
            "profanity_category": None
        }
        
        if hasattr(seg, 'customer_analysis'):
            analysis = seg.customer_analysis
            seg_data.update({
                "logical_label": analysis.label,
                "logical_type": analysis.label_type,
                "risk_score": analysis.score_risk,
                "is_profanity": analysis.is_profanity,
                "profanity_category": analysis.profanity_category
            })
            
        result_segments.append(seg_data)
    
    return {
        "id": recording.id,
        "session_id": recording.session_id,
        "file_name": recording.file_name,
        "created_at": recording.created_at,
        "segments": result_segments
    }


@router.post('/{session_id}/confirm', auth=JWTAuth())
def update_speaker_labels(request, session_id: str, payload: SpeakerUpdateSchema):
    
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    current_segments = {
        seg.id: seg
        for seg in SpeakerSegment.objects.filter(session_id=recording)
    }
    
    update_list = []

    for item in payload.segments:
        seg = current_segments.get(item.id)
        if not seg:
            continue
        new_label = 'counselor' if item.is_counselor else 'client'

        if seg.text != item.text or seg.speaker_label != new_label:
            seg.text = item.text
            seg.speaker_label = new_label
            update_list.append(seg)

    if update_list:
        SpeakerSegment.objects.bulk_update(update_list, ['text', 'speaker_label'])

    return {"status": "success", "updated_segments": len(update_list)}