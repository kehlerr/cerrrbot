import logging
from datetime import datetime
from typing import Optional

import pyotp

from common import AppResult
from settings import OTP_SECRET_KEY

logger = logging.getLogger(__name__)

otp = pyotp.TOTP(OTP_SECRET_KEY)


class AuthSession:

    default_ttl = 10 * 60

    def __init__(self, ttl: Optional[int] = None):
        self._active_until = 0
        self._ttl = ttl or self.default_ttl

    def try_authorize(self, passphrase: str) -> AppResult:
        if not otp.verify(passphrase):
            result = AppResult(
                False, f"Invalid passphrase for authorization: {passphrase}"
            )
            logger.warning(result.info)
            return result

        if self.is_active:
            result = AppResult(False, "Tried to activate already active session")
            logger.warning(result.info)
            return result

        self.authorize()
        return AppResult(True)

    def authorize(self):
        self._active_until = datetime.now().timestamp() + self._ttl

    @property
    def is_active(self):
        return datetime.now().timestamp() < self._active_until
