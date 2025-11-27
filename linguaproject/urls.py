from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI
from . import views as main_views

from accounts.api import router as accounts_router
from emotion_analysis.api import router as emotion_router
from audio_process.api import router as audio_router
from logical_analysis.api import router as logical_router
from solution_system.api import router as solution_router

api = NinjaAPI()
api.add_router("/account", accounts_router)
api.add_router("/emotion", emotion_router)
api.add_router("/audio", audio_router)
api.add_router("/logic", logical_router)
api.add_router("/solution", solution_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", api.urls),

    path('', main_views.index, name='index'),
    path('',include('accounts.urls')),
]