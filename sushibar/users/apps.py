from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'sushibar.users'
    verbose_name = "SushiBar Users"

    def ready(self):
        """Override this to put in:
            Users system checks
            Users signal registration
        """
        pass
