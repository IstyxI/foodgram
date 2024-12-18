from django.db import models


class UserRoles(models.TextChoices):
    """Варианты ролей."""

    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
