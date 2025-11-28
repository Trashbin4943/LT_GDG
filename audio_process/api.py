from ninja import Router, File, UploadedFile
from django.shortcuts import get_object_or_404
from .models import CallRecording, SpeakerSegment
from accounts.jwt_auth import JWTAuth

from django.utils import timezone
from datetime import date, datetime, time
from typing import List, Optional

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

@router.get("/list", response=List[RecordingListSchema], auth=JWTAuth())
def get_recording_list(request, target_date: date):
    naive_start = datetime.combine(target_date, time.min)
    naive_end = datetime.combine(target_date, time.max)

    start_aware = timezone.make_aware(naive_start)
    end_aware = timezone.make_aware(naive_end)

    recordings = CallRecording.objects.filter(
        uploader=request.user,
        created_at__range=(start_aware, end_aware)
    ).order_by('-created_at')

    return recordings


@router.post("/upload", auth=JWTAuth(), response=RecordingUploadResponse)
def upload_and_process(request, file: UploadedFile = File(...)):
    print("요청자: ", request.user)
    local_wav_path = None
    
    try:
        recording = CallRecording.objects.create(
            audio_file=file,
            file_name=file.name,
            uploader=request.user
        )
        print(f"DB 저장 완료. S3 경로: {recording.audio_file}")
        print(f"S3 URL: {recording.audio_file.url}")
        
    except Exception as e:
        print(f"파일 업로드 및 DB 저장 실패: {e}")
        return 500, {"status":"error", "message":f"업로드 실패: {e}", "id": None, "session_id": None}

    try:
        local_wav_path = download_and_convert_to_wav(recording.audio_file)
        print(f"분석 시작: {local_wav_path}")
        
        segments_data = transcribe_with_timestamps(local_wav_path)
        
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
        SpeakerSegment.objects.bulk_create(objs)
        
        recording.processed = True
        recording.duration = segments_data[-1]['end'] if segments_data else 0.0
        recording.save()
        
        return {
            "status": "success",
            "id": recording.id,
            "session_id": str(recording.session_id),
            "message": "업로드 및 분석이 완료되었습니다."
        }
    
    except Exception as e:
        print(f"분석 과정 중 오류 발생: {e}")
        raise e

    finally:
        cleanup_temp_file(local_wav_path)


@router.get('/{session_id}', response=RecordingDetailSchema, auth=JWTAuth())
def get_recording_detail(request, session_id: str):
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    audio_url = recording.audio_file.url if recording.audio_file else None
    
    segments = recording.segments.select_related('customer_analysis').all().order_by('turn_index')
    
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
            "profanity_category": None,
            "intensity": 0.0,
            "intensity_level": "LOW",
            "is_immoral": False,
            "immorality_confidence": 0.0
        }
        
        if hasattr(seg, 'customer_analysis'):
            analysis = seg.customer_analysis
            seg_data.update({
                "logical_label": analysis.label,
                "logical_type": analysis.label_type,
                "risk_score": analysis.score_risk,
                "is_profanity": analysis.is_profanity,
                "profanity_category": analysis.profanity_category,
                
                "intensity": analysis.intensity or 0.0,
                "intensity_level": analysis.intensity_level or "LOW",
                "is_immoral":analysis.is_immoral or False,
                "immorality_confidence":analysis.immorality_confidence or 0.0
            })
            
        result_segments.append(seg_data)
    
    return {
        "id": recording.id,
        "session_id": recording.session_id,
        "file_name": recording.file_name,
        "created_at": recording.created_at,
        "audio_url": audio_url,
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