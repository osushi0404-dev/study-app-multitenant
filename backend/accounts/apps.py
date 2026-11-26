from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'ユーザーアカウント'

    def ready(self):
        import accounts.signals  # noqa: F401
        import accounts.checks  # noqa: F401  パスキーの設定のシステムチェック（I619）
