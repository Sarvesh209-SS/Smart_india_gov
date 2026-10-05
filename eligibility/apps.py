from django.apps import AppConfig
from importlib import import_module


class EligibilityConfig(AppConfig):
    name = "eligibility"

    def ready(self):
        import_module("eligibility.signals")
