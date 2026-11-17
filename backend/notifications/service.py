from django.db import IntegrityError, transaction

from .models import DeviceToken, Notification
from .push import get_push_sender


def notify(user, kind, title, body, data=None, dedupe_key=None):
    """Store the notification and try to push it. With a dedupe_key, a second
    call for the same user and key does nothing (timed reminders run often)."""
    if dedupe_key and Notification.objects.filter(user=user, dedupe_key=dedupe_key).exists():
        return None
    try:
        with transaction.atomic():
            n = Notification.objects.create(user=user, kind=kind, title=title[:150], body=body[:500],
                                            data=data or {}, dedupe_key=dedupe_key)
    except IntegrityError:
        return None
    # Push only after the database change is saved for good (never for a rolled-back booking).
    transaction.on_commit(lambda: push(n.id))
    return n


def push(notification_id):
    n = Notification.objects.filter(pk=notification_id).first()
    if n is None:
        return
    tokens = list(DeviceToken.objects.filter(user_id=n.user_id).values_list("token", flat=True))
    sender = get_push_sender()
    if not sender.configured:
        status, error = "not_configured", ""
    elif not tokens:
        status, error = "no_device", ""
    else:
        try:
            status, error = sender.send(tokens, n.title, n.body, n.data)
        except Exception as e:  # a push failure must never break anything else
            status, error = "failed", str(e)[:300]
    Notification.objects.filter(pk=n.pk).update(push_status=status, push_error=error)


def notify_managers(kind, title, body, data=None, dedupe_key=None):
    from accounts.models import User

    for m in User.objects.filter(role=User.Role.MANAGER, is_active=True):
        notify(m, kind, title, body, data, dedupe_key)
