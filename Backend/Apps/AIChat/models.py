from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class AIChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_chats')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.created_at < timezone.now() - timedelta(days=365)

    def __str__(self):
        return f"Chat by {self.user.username} at {self.created_at}" 
