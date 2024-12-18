from django.contrib.auth.models import AbstractUser
from django.db import models

from users.enums import UserRoles
from .validators import validate_username_email


class User(AbstractUser):
    """Модель пользователя."""

    username = models.CharField(
        max_length=150,
        verbose_name='Никнейм',
        unique=True,
        db_index=True,
        validators=(validate_username_email,)
    )
    password = models.CharField(
        max_length=150,
        verbose_name='Пароль',
        blank=True
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
        blank=True
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
        blank=True
    )
    email = models.EmailField(
        max_length=150,
        verbose_name='Email',
        unique=True,
        validators=(validate_username_email,)
    )
    avatar = models.ImageField(
        upload_to='images/avatars/',
        null=True,
        default=None
    )

    class Meta:
        ordering = ('username', 'id')
        verbose_name = 'User'
        verbose_name_plural = 'Пользователи'

        def __str__(self):
            return self.username

    @property
    def is_admin(self):
        return self.role == UserRoles.ADMIN or self.is_superuser

    @property
    def is_moderator(self):
        return self.role == UserRoles.MODERATOR

    @property
    def is_user(self):
        return self.role == UserRoles.USER
