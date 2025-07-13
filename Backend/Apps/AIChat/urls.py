from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.AIChatAPIView.as_view(), name='ai_chat'),
]
