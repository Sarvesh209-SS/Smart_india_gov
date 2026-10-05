from dataclasses import dataclass, field
from documents.models import Document
from django.utils import timezone
from django.utils.translation import gettext as _

ELIGIBLE, NOT_ELIGIBLE, INCOMPLETE = "ELIGIBLE", "NOT_ELIGIBLE", "INCOMPLETE"


@dataclass
class Result:
    status: str
    met: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def get_status_display(self):
        return {
            ELIGIBLE: _("Eligible to apply"),
            NOT_ELIGIBLE: _("Not eligible"),
            INCOMPLETE: _("More information required"),
        }[self.status]


def _csv(value):
    return {item.strip().casefold() for item in value.split(",") if item.strip()}


def _age(birth_date, today=None):
    today = today or timezone.localdate()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def evaluate(profile, scholarship):
    """Preliminary check only; never legally authoritative."""
    r, rule = Result(ELIGIBLE), scholarship.rule
    if rule.min_age is not None or rule.max_age is not None:
        if not profile.date_of_birth:
            r.missing.append(_("Date of birth"))
        elif profile.date_of_birth > timezone.localdate():
            r.failed.append(_("Date of birth cannot be in the future"))
        else:
            age = _age(profile.date_of_birth)
            if rule.min_age is not None and age < rule.min_age:
                r.failed.append(_("Age %(age)s is below the minimum age of %(limit)s") % {"age": age, "limit": rule.min_age})
            elif rule.max_age is not None and age > rule.max_age:
                r.failed.append(_("Age %(age)s is above the maximum age of %(limit)s") % {"age": age, "limit": rule.max_age})
            else:
                r.met.append(_("Age requirement"))

    if rule.max_income is not None:
        if profile.annual_family_income is None:
            r.missing.append(_("Annual family income"))
        elif profile.annual_family_income > rule.max_income:
            r.failed.append(_("Income exceeds limit of %(limit)s") % {"limit": rule.max_income})
        else:
            r.met.append(_("Income limit"))

    profile_rules = (
        (_("Education level"), profile.education_level, rule.education_levels),
        (_("Category"), profile.category, rule.categories),
        (_("State"), profile.state, rule.states),
    )
    for label, value, allowed_values in profile_rules:
        allowed = _csv(allowed_values)
        if not allowed:
            continue
        normalized_value = (value or "").strip().casefold()
        if not normalized_value:
            r.missing.append(label)
        elif normalized_value not in allowed:
            r.failed.append(_("%(label)s '%(value)s' is not in the listed criteria") % {"label": label, "value": value.strip()})
        else:
            r.met.append(label)

    if rule.requires_first_gen:
        if profile.first_generation_graduate is None:
            r.missing.append(_("First-generation status"))
        elif not profile.first_generation_graduate:
            r.failed.append(_("First-generation graduate required"))
        else:
            r.met.append(_("First-generation graduate"))

    documents_by_type = {}
    user_documents = Document.objects.filter(owner=profile.user).values_list("doc_type_id", "status")
    for document_type_id, status in user_documents:
        documents_by_type.setdefault(document_type_id, set()).add(status)

    for dt in rule.required_documents.all():
        statuses = documents_by_type.get(dt.id, set())
        if Document.Status.VERIFIED in statuses:
            r.met.append(_("Verified document: %(name)s") % {"name": dt.display_name})
        elif statuses:
            current = ", ".join(sorted(str(Document.Status(status).label) for status in statuses))
            r.missing.append(_("%(name)s document must be verified (current status: %(status)s)") % {"name": dt.display_name, "status": current})
        else:
            r.missing.append(_("Document: %(name)s") % {"name": dt.display_name})

    r.status = NOT_ELIGIBLE if r.failed else INCOMPLETE if r.missing else ELIGIBLE
    return r
