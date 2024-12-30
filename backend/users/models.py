from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель для пользователей созданная для приложения foodgram"""

    email = models.EmailField(verbose_name="Электронная почта", unique=True)
    username = models.CharField(
        max_length=150, verbose_name="Имя пользователя", unique=True, db_index=True
    )
    first_name = models.CharField(max_length=150, verbose_name="Имя")
    last_name = models.CharField(max_length=150, verbose_name="Фамилия")
    avatar = models.ImageField(upload_to="images/avatars/", null=True, default=None)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("username", "id")

    def __str__(self):
        """Строковое представление модели."""
        return self.username
