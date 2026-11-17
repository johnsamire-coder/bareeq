"""How one-time codes reach the customer.

The SMS company is not chosen yet (SPEC 2). Until then ConsoleOtpSender
writes the code to the server log. To add a real company later, write a new
class with the same send() method and point OTP_SENDER in backend/.env to it.
"""
import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger("bareeq.otp")


class OtpSender:
    def send(self, phone: str, code: str) -> None:
        raise NotImplementedError


class ConsoleOtpSender(OtpSender):
    def send(self, phone, code):
        logger.warning("OTP for %s: %s", phone, code)


def get_otp_sender() -> OtpSender:
    return import_string(settings.OTP_SENDER)()
