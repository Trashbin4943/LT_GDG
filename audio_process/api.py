from ninja import Router, File, UploadedFile
from django.shortcuts import get_object_or_404
from .models import CallRecording, SpeakerSegment
from .audio_system.diarization.speaker_split import transcribe_with_timestamps
from .audio_system.utils.audio_utils import download_and_convert_to_wav, cleanup_temp_file
from ninja_jwt.authentication import JWTAuth
from typing import List
from .schemas import (
    RecordingListSchema, 
    RecordingDetailSchema, 
    RecordingUploadResponse, # [필수] 업로드 응답 스키마
    SpeakerSegmentSchema, 
    SpeakerUpdateSchema
)

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
                # [수정 1] 모델 FK 필드명이 'session_id'이므로 여기에 recording 객체 할당
                session_id=recording, 
                
                # [수정 2] bulk_create는 save()를 안 타므로, 여기서 직접 인덱스 할당 필수
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
            "id": recording.id,                 # 상세 페이지 이동용 DB ID
            "session_id": str(recording.session_id), # UUID 세션 ID
            "message": "업로드 및 분석이 완료되었습니다."
        }

    except Exception as e:
        print(f"Error: {e}")
        # 에러 발생 시 500 응답 처리 (Ninja가 처리)
        raise e

    finally:
        cleanup_temp_file(local_wav_path)


@router.get("/list", response=List[RecordingListSchema], auth=JWTAuth())
def get_recording_list(request):
    # (필요 시 날짜 필터 로직 추가)
    recordings = CallRecording.objects.filter(
        uploader=request.user
    ).order_by('-created_at')
    return recordings


@router.get('/{session_id}', response=RecordingDetailSchema, auth=JWTAuth())
def get_recording_detail(request, session_id: str):
    # session_id(UUID)로 조회
    recording = get_object_or_404(CallRecording, session_id=session_id, uploader=request.user)
    
    # segments 역참조 (모델에서 related_name='segments'로 설정됨)
    segments = recording.segments.all().order_by('turn_index') # turn_index로 정렬
    
    result_segments = []
    
    for seg in segments:
        # 기본 데이터 매핑
        seg_data = {
            "id": seg.id,
            "speaker_label": seg.speaker_label,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text,
            "emotion_label": seg.emotion_label,
            "emotion_confidence": seg.emotion_confidence,
            
            # 논리 분석 결과 초기값
            "logical_label": None,
            "logical_type": None,
            "risk_score": 0.0,
            "is_profanity": False,
            "profanity_category": None
        }
        
        # [연결] CustomerAnalysisResult 데이터가 있으면 덮어쓰기
        # OneToOne 관계이므로 hasattr로 확인 가능
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
    
    # FK 필드명 session_id로 필터링
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