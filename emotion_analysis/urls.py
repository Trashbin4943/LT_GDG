from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from emotion_analysis.api import router as emotion_router
from . import views

api = NinjaAPI(auth=None)  # 기본 API 객체 생성

# router 등록
api.add_router("/emotion", emotion_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),   # Ninja API 엔드포인트
    path("analyze-emotion/",views.analyze_emotion, name="analyze-emotion")
]
