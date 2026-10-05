from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification
def notify(user, kind, title, body, ref, url=""):
    n, created = Notification.objects.get_or_create(
        user=user, kind=kind, ref=ref, defaults=dict(title=title, body=body, url=url))
    if created:  # push only once per opportunity
        async_to_sync(get_channel_layer().group_send)(f"user_{user.id}", {
            "type": "notify", "payload": {"id": n.id, "kind": kind, "title": title, "body": body, "url": url}})
    return n
