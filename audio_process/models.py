import os
from django.db import models, transaction
from django.db.models import Max
from django.conf import settings
from django.utils import timezone
import uuid

def upload_path(instance, filename):
    now = timezone.now()
    ext = filename.split('.')[-1]
    return f"raw_calls/{now.strftime('%Y/%m/%d')}/{instance.session_id}.{ext}"

class CallRecording(models.Model):
    session_id = models.CharField(
        max_length=255, 
        unique=True, 
        default=uuid.uuid4, 
        editable=False,
        db_index=True
    )

    audio_file = models.FileField(
        upload_to=upload_path, 
        verbose_name="녹음 파일"
    )

    file_name = models.CharField(max_length=255, blank=True)
    
    processed = models.BooleanField(default=False)
    duration = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='recordings'
    )

    def __str__(self):
        return f"[{self.created_at.date()}] {self.session_id}"

    class Meta:
        db_table = 'call_recordings'
        ordering = ['-created_at']


class SpeakerSegment(models.Model):
    session_id = models.ForeignKey(CallRecording, on_delete=models.CASCADE, related_name='segments')
    turn_index = models.IntegerField(editable=False, null=True)
    speaker_label = models.CharField(max_length=50)
    is_counselor = models.BooleanField(default=False)
    start_time = models.FloatField()
    end_time = models.FloatField()
    text = models.TextField()
    emotion_label = models.CharField(max_length=50, null=True, blank=True)
    emotion_confidence = models.FloatField(null=True, blank=True)
    
    
    class Meta:
        db_table = 'speaker_segments'
        ordering = ['session_id','turn_index']

    def save(self, *args, **kwargs):
        """
        저장 시점에 자동으로 turn_index를 계산하여 할당
        """
        # 1. turn_index가 없는 경우에만 계산 (새로 생성 시)
        if self.turn_index is None:
            
            # 2. 동시성 제어를 위한 트랜잭션 시작
            with transaction.atomic():
                # 해당 세션의 데이터들을 잠금(Lock) 걸어서 다른 요청이 끼어들지 못하게 함
                # (성능을 위해 필요한 만큼만 필터링)
                qs = SpeakerSegment.objects.filter(session_id=self.recording).select_for_update()
                
                # 3. 현재 가장 큰 turn_index 조회
                max_index = qs.aggregate(Max('turn_index'))['turn_index__max']
                
                # 4. 다음 번호 할당
                if max_index is None:
                    self.turn_index = 0  # 첫 데이터면 0번 시작
                else:
                    self.turn_index = max_index + 1
                    
                # 5. 부모의 save 호출 (실제 DB 저장)
                super().save(*args, **kwargs)
        else:
            # 이미 turn_index가 있으면 그냥 저장 (수정의 경우)
            super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.session_id}] Turn {self.turn_index}"