from rest_framework import serializers
from .models import AIChatMessage

class AIChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatMessage
        fields = ['message', 'response', 'created_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Format datetime as ISO string
        rep['created_at'] = instance.created_at.isoformat() if instance.created_at else None
        return rep
