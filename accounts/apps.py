from django.apps import AppConfig
from django_redis import get_redis_connection


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'