import jwt
from django.conf import settings
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        return User.objects.get(id=user_id)
    except Exception:
        return None

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser
        # Get token from query string or headers
        token = None
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        if 'token' in query_params:
            token = query_params['token'][0]
        else:
            headers = dict((k.decode(), v.decode()) for k, v in scope.get('headers', []))
            auth_header = headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        user = None
        if token:
            user = await get_user_from_token(token)
        scope['user'] = user if user else AnonymousUser()
        return await self.app(scope, receive, send)

