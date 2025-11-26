# from celery import shared_task
# from .models import CallRecording, SpeakerSegment
# from .utils import download_and_convert_to_wav, cleanup_temp_file
# from .services import diarize_and_transcribe

# @shared_task
# def process_audio_analysis(recording_id):
#     """
#     [백그라운드 워커] 오디오 분석 작업 수행
#     """
#     print(f"👷 [Celery] 작업 시작: Recording ID {recording_id}")
#     try:
#         recording = CallRecording.objects.get(id=recording_id)
#         local_wav_path = download_and_convert_to_wav(recording.audio_file)
#         segments_data = diarize_and_transcribe(local_wav_path)
        
#         objs = [
#             SpeakerSegment(
#                 recording=recording,
#                 speaker_label=item['speaker'],
#                 start_time=item['start'],
#                 end_time=item['end'],
#                 text=item['text']
#             ) for item in segments_data
#         ]
#         SpeakerSegment.objects.bulk_create(objs)
        
#         recording.processed = True
#         if segments_data:
#             recording.duration = segments_data[-1]['end'] # 마지막 발화 끝나는 시간 = 총 길이
#         recording.save()
        
#         return {
#             "status": "success",
#             "session_id": recording.session_id,
#             "uploader": recording.uploader.korean_name, # 확인용 리턴
#             "segments_count": len(objs),
#             "s3_url": recording.audio_file.url
#         }

#     except Exception as e:
#         print(f"에러 발생: {e}")
#         return {"status": "error", "message": str(e)}

#     finally:
#         cleanup_temp_file(local_wav_path)