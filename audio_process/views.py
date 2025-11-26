from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import CallRecording

@login_required
def recording_list_view(request):
    """
    녹음 파일 목록을 보여주는 페이지
    """
    return render(request, 'index.html')

@login_required
def correction_view(request, session_id):
    """수정 및 화자 분리 페이지 렌더링"""
    # 존재하는 세션인지 확인 (404 방지)
    get_object_or_404(CallRecording, session_id=session_id)
    return render(request, 'audio/correction.html', {'session_id': session_id})

@login_required
def dashboard_view(request, session_id):
    """분석 결과 대시보드 페이지 렌더링"""
    get_object_or_404(CallRecording, session_id=session_id)
    return render(request, 'audio/dashboard.html', {'session_id': session_id})