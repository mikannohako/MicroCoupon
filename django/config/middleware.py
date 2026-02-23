import base64
import binascii

from django.conf import settings
from django.http import HttpResponse


class AdminBasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        admin_path = settings.ADMIN_PATH or 'admin/'
        normalized = '/' + admin_path.lstrip('/')
        if not normalized.endswith('/'):
            normalized += '/'
        self.admin_prefix = normalized
        self.realm = settings.ADMIN_BASIC_AUTH_REALM
        self.enabled = bool(
            settings.ADMIN_BASIC_AUTH_USER and settings.ADMIN_BASIC_AUTH_PASSWORD
        )

    def __call__(self, request):
        if self.enabled and request.path.startswith(self.admin_prefix):
            if not self._authorized(request):
                return self._unauthorized_response()
        return self.get_response(request)

    def _authorized(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Basic '):
            return False
        try:
            encoded = auth_header.split(' ', 1)[1]
            decoded = base64.b64decode(encoded).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return False
        username, _, password = decoded.partition(':')
        return (
            username == settings.ADMIN_BASIC_AUTH_USER
            and password == settings.ADMIN_BASIC_AUTH_PASSWORD
        )

    def _unauthorized_response(self):
        response = HttpResponse(status=401)
        response['WWW-Authenticate'] = f'Basic realm="{self.realm}"'
        return response
