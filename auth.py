import pyotp
import logging
from typing import Optional, Union, Dict, Any

from common import AppResponse
from settings import OTP_SECRET_KEY


logger = logging.getLogger("main")

otp = pyotp.TOTP(OTP_SECRET_KEY)


class AuthSession:

    default_ttl = 30*60

    def __init__(self, ttl: Optional[int] = None):
        self._active_until = 0
        self._ttl = ttl or self.default_ttl

    def try_authorize(self, passphrase: str) -> AppResponse:
        if not otp.verify(passphrase):
            app_response = AppResponse(False, f"Invalid passphrase for authorization: {passphrase}")
            logger.warning(app_response.result_info)
            return app_response

        if self.is_active:
            app_response = AppResponse(False, f"Tried to activate already active session")
            logger.warning(app_response.result_info)
            return app_response

        self.authorize()
        return AppResponse(True)

    def authorize(self):
        self._active_until = datetime.now() + self._ttl

    @property
    def is_active(self):
        return datetime.now() < self._active_until


