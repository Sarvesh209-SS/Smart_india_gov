from django.conf import settings
from django.db import models
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, db_index=True)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=300)
    ref = models.CharField(max_length=60)  # dedupe key, e.g. "sch-12"
    url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("user", "kind", "ref")]
        ordering = ["-created_at"]
