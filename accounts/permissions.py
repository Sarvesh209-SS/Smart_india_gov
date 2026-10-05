REVIEWER_ROLES = {"REVIEWER", "ADMIN", "SUPER_ADMIN"}
ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN"}


def can_review_documents(user):
    return user.is_authenticated and user.is_staff and user.role in REVIEWER_ROLES


def can_manage_roles(user):
    return user.is_authenticated and user.is_superuser and user.role == "SUPER_ADMIN"
