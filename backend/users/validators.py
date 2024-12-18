import re

from django.core.exceptions import ValidationError


def validate_username_email(name):
    """Валидатор имени пользователя."""
    if name == 'me':
        raise ValidationError('Имя "me" использовать запрещено!')
    if not re.compile(r'^[\w.@+-]+').fullmatch(name):
        raise ValidationError(
            'Можно использовать только буквы, цифры и символы @.+-_".'
        )
