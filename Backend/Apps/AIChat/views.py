from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.models import User
from Apps.Properties.models import Property
from .models import AIChatMessage
import os
from dotenv import load_dotenv
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

class AIChatAPIView(APIView):
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'Authorization',
                openapi.IN_HEADER,
                description="JWT token. Format: Bearer <access_token>",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['user_id', 'message'],
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'message': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: openapi.Response('AI chat response'), 400: 'Bad Request'}
    )
    def post(self, request):
        user_id = request.data.get('user_id')
        message = request.data.get('message')
        if not user_id or not message:
            return Response({'error': 'user_id and message are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user making the request matches the JWT user
        if request.user.id != int(user_id):
            return Response({'error': 'Unauthorized: user_id does not match authenticated user.'}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        # Only include non-sensitive backend info in context
        backend_info = (
            "Welcome! You are chatting with the Airbnb Clone backend assistant. "
            "Your messages are secure and private. "
            "Feel free to ask general questions about your account or available features. "
            "For your safety, sensitive information and internal system details are never shared."
        )
        context = backend_info
        property_list = []

        # Call Gemini API (example, replace with actual endpoint)
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": context}]},
                {"role": "user", "parts": [{"text": message}]}
            ]
        }
        params = {"key": GEMINI_API_KEY}
        ai_response = ""
        try:
            r = requests.post(gemini_url, json=payload, headers=headers, params=params)
            if r.status_code == 200:
                ai_response = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            else:
                ai_response = f"Gemini API error: {r.text}"
        except Exception as e:
            ai_response = f"Error calling Gemini API: {str(e)}"

        # Save chat
        AIChatMessage.objects.create(user=user, message=message, response=ai_response)

        return Response({
            'reply': ai_response,
            'properties': property_list
        }, status=status.HTTP_200_OK)
