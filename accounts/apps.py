from django.apps import AppConfig
from importlib import import_module


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        import_module("accounts.signals")
