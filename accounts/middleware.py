from django.contrib.auth import logout
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin


class PreferredLanguageMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user
        if user.is_authenticated and user.preferred_language:
            translation.activate(user.preferred_language)
            request.LANGUAGE_CODE = user.preferred_language
        return None


class SessionVersionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user
        if not user.is_authenticated:
            return None
        session_version = request.session.get("auth_version")
        if session_version != user.auth_version:
            logout(request)
            return None
        request.session["auth_version"] = user.auth_version
        return None
