import json
from channels.generic.websocket import AsyncWebsocketConsumer
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

class AIChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept all connections for testing
        await self.accept()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '')
        except Exception:
            await self.send(text_data=json.dumps({
                'error': 'Invalid or empty JSON message. Please send {"message": "your text"}.'
            }))
            return

        # Only include non-sensitive backend info in context
        backend_info = (
            "Backend Overview: This project uses Django and Django REST Framework. "
            "It includes models for properties, bookings, payments, reviews, images, and AI chat messages. "
            "Endpoints support JWT authentication, property management, booking, payment, review, and AI chat. "
            "Swagger is enabled for API documentation and testing. "
            "Sensitive data such as user names, states, property ownership, and booking details are not accessible. "
            "You can ask about available models, endpoints, features, authentication, and general backend structure."
        )
        context = backend_info
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

        # Save chat to database
        try:
            from .models import AIChatMessage
            user = self.scope['user']
            if user.is_authenticated:
                AIChatMessage.objects.create(user=user, message=message, response=ai_response)
        except Exception as db_exc:
            pass  # Optionally log db_exc

        await self.send(text_data=json.dumps({
            'reply': ai_response
        }))
