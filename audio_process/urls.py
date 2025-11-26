from django.urls import path
from . import views

app_name = 'audio'

urlpatterns = [
    # 1. 녹음 파일 목록 (선택 사항)
    path('list/', views.recording_list_view, name='list'),
    
    # 2. (구 detail) 수정 및 화자 지정 페이지
    # URL: /audio/correction/abc-123/
    path('correction/<str:session_id>/', views.correction_view, name='correction'),

    # 3. (신규) 분석 결과 및 솔루션 대시보드
    # URL: /audio/dashboard/abc-123/
    path('dashboard/<str:session_id>/', views.dashboard_view, name='dashboard'),
]