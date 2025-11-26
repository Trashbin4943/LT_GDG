from django.urls import path
from solution_system.api import api as solution_api

urlpatterns = [
    path("api/solution/", solution_api.urls),
]