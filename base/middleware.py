# base/middleware.py
from django.utils.deprecation import MiddlewareMixin

class SessionFixationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method == 'POST' and 'otp' in request.session:
            # Ensure session is saved before OTP verification
            request.session.save()