from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Q
from profiles.models import UserProfile
from scholarships.models import Scholarship
from notifications.services import notify
from .engine import evaluate, ELIGIBLE
@receiver(post_save, sender=UserProfile)
def match_on_profile_update(sender, instance, **kw):
    if sender is not UserProfile or kw.get("raw"):
        return
    today = timezone.localdate()
    qs = (Scholarship.objects.filter(is_published=True, rule__isnull=False)
          .filter(Q(closes_on__isnull=True) | Q(closes_on__gte=today)))
    for s in qs:
        if evaluate(instance, s).status == ELIGIBLE:
            notify(instance.user, "OPPORTUNITY", "New Opportunity",
                   f"You may be eligible to apply for {s.name}.", ref=f"sch-{s.pk}", url=s.official_url)
