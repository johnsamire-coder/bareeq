"""Sending to phones. The Firebase project does not exist yet, so the default
sender only records that push is not configured. When it arrives: write
FirebasePushSender with the same send() and set PUSH_SENDER in backend/.env."""
import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger("bareeq.push")


class PushSender:
    configured = False

    def send(self, tokens, title, body, data):
        """Returns (status, error)."""
        raise NotImplementedError


class NotConfiguredPushSender(PushSender):
    def send(self, tokens, title, body, data):
        logger.info("push (not configured) to %d device(s): %s", len(tokens), title)
        return "not_configured", ""


def get_push_sender():
    return import_string(getattr(settings, "PUSH_SENDER", "notifications.push.NotConfiguredPushSender"))()
