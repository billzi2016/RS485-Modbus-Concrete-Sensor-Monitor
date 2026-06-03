from django.apps import AppConfig


class MonitorAppConfig(AppConfig):
    """Django 标准应用配置，保持最传统的 app 组织方式。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "app"
    verbose_name = "RS485 Monitor App"
