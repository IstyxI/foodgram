import base64

from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import User


class Base64ImageField(serializers.ImageField):
    """Сериализатор изображения в кодировке base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор данных при создании пользователя."""

    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'password', 'first_name',
            'last_name', 'email', 'avatar',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        """Запрещает использовать повторно username и email."""
        if User.objects.filter(username=data.get('username')).exists():
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует'
            )
        return data
