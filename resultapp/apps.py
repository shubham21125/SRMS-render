from django.apps import AppConfig


class ResultappConfig(AppConfig):
    name = 'resultapp'

    def ready(self):
        import resultapp.signals
