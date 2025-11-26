from ninja import Router, File, UploadedFile, Schema
from django.shortcuts import get_object_or_404
from .models import CallRecording, SpeakerSegment
from ninja_jwt.authentication import JWTAuth
from datetime import date, datetime

class RecordingUploadResponse(Schema):
    id: int
    session_id: str
    message: str

class RecordingListSchema(Schema):
    id: int
    session_id: str
    file_name: str
    created_at: datetime
    duration: float
    processed: bool

class SpeakerSegmentSchema(Schema):
    id: int
    speaker_label: str
    start_time: float
    end_time: float
    text: str | None = None

    # 1. 감정 분석 결과 (Emotion)
    emotion_label: str | None = None
    emotion_confidence: float | None = None

    # 2. 논리 분석 결과 (Logical Analysis)
    logical_label: str | None = None       # 예: COMPLAINT, PROFANITY
    logical_type: str | None = None        # 예: NORMAL, SPECIAL
    risk_score: float | None = None        # 예: 0.85
    is_profanity: bool | None = None       # 욕설 여부

    profanity_category: str | None = None

class SegmentUpdateSchema(Schema):
    id: int
    text: str | None = None
    is_counselor: bool

class RecordingDetailSchema(Schema):
    id: int
    session_id: str
    file_name: str
    created_at: datetime
    segments: list[SpeakerSegmentSchema]

class SpeakerUpdateSchema(Schema):
    segments: list[SegmentUpdateSchema]



