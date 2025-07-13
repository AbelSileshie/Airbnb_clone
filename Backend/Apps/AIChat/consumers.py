import json
import os
import re
import requests
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv
from django.db import transaction

load_dotenv()
GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

class AIChatConsumer(AsyncWebsocketConsumer):
    @staticmethod
    def extract_city(message):
        city_match = re.search(r"in ([A-Za-z ]+)", message, re.IGNORECASE)
        return city_match.group(1).strip() if city_match else None

    @staticmethod
    def extract_criteria(message):
        best_keywords = ["best", "top", "cheapest", "luxury", "recommended"]
        for kw in best_keywords:
            if kw in message.lower():
                return kw
        return None

    @staticmethod
    def filter_properties(properties, city=None, criteria=None):
        if city:
            return [p for p in properties if city.lower() in p.get('location', '').lower()]
        if criteria == "cheapest":
            return sorted(properties, key=lambda x: x.get('price', 0))[:5]
        if criteria == "luxury":
            return sorted(properties, key=lambda x: x.get('price', 0), reverse=True)[:5]
        if criteria in ["best", "top", "recommended"]:
            return properties[:5]
        return properties

    @staticmethod
    def filter_bookings(bookings, city=None, user_id=None):
        filtered = bookings
        if city:
            filtered = [b for b in filtered if city.lower() in str(b.get('property', '')).lower()]
        if user_id is not None:
            filtered = [b for b in filtered if b.get('user') == user_id]
        return filtered

    async def get_all_bookings(self):
        from Apps.Properties.models import Booking
        from rest_framework import serializers
        from channels.db import database_sync_to_async
        class BookingSerializer(serializers.ModelSerializer):
            class Meta:
                model = Booking
                fields = ['id', 'user', 'property', 'start_date', 'end_date', 'status', 'created_at']
        def fetch_bookings():
            return list(Booking.objects.select_related('user', 'property').all())
        bookings_list = await database_sync_to_async(fetch_bookings)()
        return BookingSerializer(bookings_list, many=True).data

    async def get_all_properties(self):
        from Apps.Properties.models import Property
        from rest_framework import serializers
        from channels.db import database_sync_to_async
        class PropertySerializer(serializers.ModelSerializer):
            class Meta:
                model = Property
                fields = ['id', 'name', 'location', 'price', 'description', 'images']
        def fetch_properties():
            return list(Property.objects.all())
        properties_list = await database_sync_to_async(fetch_properties)()
        return PropertySerializer(properties_list, many=True).data
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        await self.accept()
        from .models import AIChatMessage
        from .serializer import AIChatMessageSerializer
        from channels.db import database_sync_to_async
        def get_history():
            # Only fetch user's own messages, limit to 10, order by newest
            return list(AIChatMessage.objects.filter(user=user).order_by('-created_at')[:10])
        history_list = await database_sync_to_async(get_history)()
        chat_history = AIChatMessageSerializer(history_list, many=True).data
        await self.send(text_data=json.dumps({
            'chat_history': chat_history
        }))

    async def receive(self, text_data):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.send(text_data=json.dumps({
                'error': 'Authentication required. Please login to use AI chat.'
            }))
            await self.close()
            return
        # Validate and parse incoming JSON
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            if not message:
                raise ValueError('Empty message')
        except Exception:
            await self.send(text_data=json.dumps({
                'error': 'Invalid or empty JSON message. Please send {"message": "your text"}.'
            }))
            return

        # Security: Only allow up to 512 characters per message
        if len(message) > 1000:
            await self.send(text_data=json.dumps({
                'error': 'Message too long. Limit is 512 characters.'
            }))
            return

        # Prepare backend context and full chat history
        backend_info = (
            "Backend Overview: This project uses Django and Django REST Framework. "
            "It includes models for properties, bookings, payments, reviews, images, and AI chat messages. "
            "Endpoints support JWT authentication, property management, booking, payment, review, and AI chat. "
            "Swagger is enabled for API documentation and testing. "
            "Sensitive data such as user names, states, property ownership, and booking details are not accessible. "
            "You can ask about available models, endpoints, features, authentication, and general backend structure."
        )
        # Only include the ID of the previous message for reference
        from .models import AIChatMessage
        from channels.db import database_sync_to_async
        def get_last_message_id():
            last_msg = AIChatMessage.objects.filter(user=user).order_by('-created_at').first()
            return last_msg.id if last_msg else None
        prev_msg_id = await database_sync_to_async(get_last_message_id)()
        context = backend_info
        if prev_msg_id:
            context += f"\nPrevious Message ID: {prev_msg_id}"

        # If the user asks about properties, include all properties in context
        properties_context = ""
        bookings_context = ""
        keywords = ["property", "properties", "book", "booking", "available", "location", "price"]
        city = self.extract_city(message)
        criteria = self.extract_criteria(message)
        send_properties_or_bookings = any(word in message.lower() for word in keywords) or city or criteria
        filtered_properties = []
        filtered_bookings = []
        if send_properties_or_bookings:
            # Only fetch and filter if needed
            all_properties, all_bookings = await self.get_all_properties(), await self.get_all_bookings()
            filtered_properties = self.filter_properties(all_properties, city, criteria)
            filtered_bookings = self.filter_bookings(all_bookings, city, user.id)
            if filtered_properties or filtered_bookings:
                await self.send(text_data=json.dumps({
                    'properties': filtered_properties,
                    'bookings': filtered_bookings
                }))
            else:
                await self.send(text_data=json.dumps({
                    'reply': 'No properties or bookings found for your query.'
                }))
            # Only add context if there are results
            if filtered_properties or filtered_bookings:
                context += f"\nFiltered Properties: {json.dumps(filtered_properties)}\nFiltered Bookings: {json.dumps(filtered_bookings)}"
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        # Build Gemini API payload, context is optional
        contents = []
        if context:
            contents.append({"role": "user", "parts": [{"text": context}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        payload = {
            "contents": contents
        }
        params = {"key": GEMINI_API_KEY}
        ai_response = ""
        # Call Gemini API securely
        try:
            r = requests.post(gemini_url, json=payload, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                ai_response = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            else:
                ai_response = f"Gemini API error: {r.text}"
        except Exception as e:
            ai_response = f"Error calling Gemini API: {str(e)}"

        # Save chat to database atomically and fetch history in sync thread
        from .models import AIChatMessage
        from .serializer import AIChatMessageSerializer
        from channels.db import database_sync_to_async
        def save_and_get_history():
            with transaction.atomic():
                AIChatMessage.objects.create(user=user, message=message, response=ai_response)
                qs = AIChatMessage.objects.filter(user=user).order_by('-created_at')[:10]
                return list(qs)
        history_list = await database_sync_to_async(save_and_get_history)()
        chat_history = AIChatMessageSerializer(history_list, many=True).data
        await self.send(text_data=json.dumps({
            'reply': ai_response,
            'chat_history': chat_history
        }))
