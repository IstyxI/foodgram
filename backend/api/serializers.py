import base64

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.validators import MinValueValidator, RegexValidator

from djoser.serializers import UserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)
from users.models import User


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для кодирования изображения в base64."""

    def to_internal_value(self, data):
        """Декодируем base64 строку в файл."""
        if isinstance(data, str) and data.startswith('data:'):
            header, encoded = data.split(';')
            _, encoded = encoded.split(',')
            decoded = base64.b64decode(encoded)
            ext = header.split('/')[-1]
            file_name = f"avatar_{self.context['request'].user.id}.{ext}"
            return ContentFile(decoded, name=file_name)
        return super().to_internal_value(data)

    def delete(self, instance, save):
        """Удаляет файл с сервера, делает avatar = None."""
        if not instance.avatar:
            return
        file_name = instance.avatar.name
        default_storage.delete(file_name)
        instance.avatar = None
        if save:
            instance.save()


class TagSerializer(ModelSerializer):
    """Сериализатор для вывода тэгов."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id",)


class IngredientSerializer(ModelSerializer):
    """Сериализатор для вывода ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class CustomUserSerializer(UserCreateSerializer):
    """Проверяет/отдаёт данные."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)
    username = serializers.CharField(
        max_length=150,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+\Z",
                message="Имя пользователя должно содержать только буквы, "
                "цифры, подчеркивания, точки, знаки @, + и -.",
            )
        ],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
        )
        read_only_fields = ("id", "password")

    def get_is_subscribed(self, obj):
        """Проверка подписки."""
        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj.id).exists()


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """Проверяет/отдаёт данные пользователя при создании."""

    class Meta:
        model = User
        fields = (
            "email", "id", "username",
            "first_name", "last_name", "password"
        )
        extra_kwargs = {"password": {"write_only": True}}


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов в рецепте."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = IngredientInRecipe
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов."""

    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientInRecipeSerializer(
        source="ingredient_list", many=True, required=True, allow_null=False
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        """Проверка на добавление в избранное."""
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверка на присутствие в корзине."""
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class CreateIngredientsInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ингредиентов в рецепте."""

    id = serializers.IntegerField(required=True)
    amount = serializers.IntegerField(
        required=True, validators=[MinValueValidator(1)]
    )

    class Meta:
        model = IngredientInRecipe
        fields = ("id", "amount")


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Создаёт/валидирует рецепты."""

    ingredients = CreateIngredientsInRecipeSerializer(
        many=True, required=True, allow_null=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    image = Base64ImageField(use_url=True)

    class Meta:
        model = Recipe
        fields = (
            "ingredients", "tags", "name",
            "image", "text", "cooking_time"
        )

    def to_representation(self, instance):
        """Метод представления модели."""
        serializer = RecipeSerializer(
            instance, context={"request": self.context.get("request")}
        )
        return serializer.data

    def validate(self, data):
        """Валидация ингредиентов."""
        tags = self.initial_data.get("tags", [])
        ingredients = self.initial_data.get("ingredients", [])

        if not ingredients:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым!"
            )

        if len(ingredients) != len(
            set(ingredient["id"] for ingredient in ingredients)
        ):
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными!"
            )

        if not tags:
            raise serializers.ValidationError("Тег не может быть None!")

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными!")
        return data

    def create_ingredients(self, ingredients, recipe):
        """Создание ингредиента."""
        ingredients_to_create = []
        for element in ingredients:
            serializer = CreateIngredientsInRecipeSerializer(data=element)
            serializer.is_valid(raise_exception=True)
            ingredient_id = serializer.validated_data["id"]
            if not Ingredient.objects.filter(pk=ingredient_id).exists():
                raise serializers.ValidationError(
                    f"Ингредиента с id {ingredient_id} не существует!"
                )
            ingredients_to_create.append(
                IngredientInRecipe(
                    ingredient_id=serializer.validated_data["id"],
                    recipe=recipe,
                    amount=serializer.validated_data["amount"],
                )
            )
        IngredientInRecipe.objects.bulk_create(ingredients_to_create)

    def create_tags(self, tags, recipe):
        """Добавление тега."""
        recipe.tags.set(tags)

    def create(self, validated_data):
        """Создание модели."""
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        user = self.context.get("request").user
        recipe = Recipe.objects.create(**validated_data, author=user)
        self.create_ingredients(ingredients, recipe)
        self.create_tags(tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Обновление модели."""
        IngredientInRecipe.objects.filter(recipe=instance).delete()

        self.create_ingredients(validated_data.pop("ingredients"), instance)
        self.create_tags(validated_data.pop("tags"), instance)

        return super().update(instance, validated_data)


class AdditionalForRecipeSerializer(serializers.ModelSerializer):
    """Дополнительный сериализатор для рецептов."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(CustomUserSerializer):
    """Используется для получения данных."""

    recipes = serializers.SerializerMethodField(
        read_only=True, method_name="get_recipes"
    )
    recipes_count = serializers.IntegerField(default=0)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
            "recipes_count",
            "recipes",
        )

    def get_recipes(self, obj):
        """Получение рецептов."""
        request = self.context.get("request")
        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get("recipes_limit", 10)
        if recipes_limit:
            recipes = recipes[: int(recipes_limit)]
        return ShortRecipeSerializer(recipes, many=True).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Краткий ериализатор для вывода данных."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class SubscriptionSerializer(serializers.ModelSerializer):
    """Создаёт/валидирует подписку на пользователя."""

    class Meta:
        model = Follow
        fields = ("user", "author")
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=("user", "author"),
            )
        ]

    def create(self, validated_data):
        """Создаёт подписку."""
        user = self.context.get("request").user
        author = User.objects.get(pk=validated_data["author"].id)
        return Follow.objects.create(user=user, author=author)

    def validate(self, data):
        """Проверки на корректность подписки."""
        user = data.get("user")
        author = data.get("author")
        if user == author:
            raise serializers.ValidationError(
                "Вы не можете подписаться на самого себя!"
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя!"
            )
        return data


class FavoriteSerializer(serializers.Serializer):
    """Сохранаяет/валидирует избранные рецепты."""

    recipe_id = serializers.IntegerField(required=True)

    def create(self, validated_data):
        """Сохранаяет рецепт в избранное."""
        user = self.context.get("request").user
        recipe = Recipe.objects.get(pk=validated_data["recipe_id"])
        return Favorite.objects.create(user=user, recipe=recipe)

    def validate(self, data):
        user = self.context.get("request").user
        recipe = data.get("recipe_id")
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                "Нельзя добавлять рецепты с одинаковыми именами, "
                "он уже есть в избранном у пользователя"
            )
        return data


class ShoppingCartSerializer(serializers.Serializer):
    """Создаёт/валидирует корзину."""

    recipe_id = serializers.IntegerField(required=True)

    def create(self, validated_data):
        user = self.context.get("request").user
        recipe = Recipe.objects.get(pk=validated_data["recipe_id"])
        return ShoppingCart.objects.create(user=user, recipe=recipe)

    def validate(self, data):
        user = self.context.get("request").user
        recipe = data.get("recipe_id")
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                "Нельзя добавлять рецепты с одинаковыми именами, "
                "он уже есть в избранном у пользователя"
            )
        return data


class DjoserCustomUserSerializer(DjoserUserSerializer):
    """Кастомный сериализатор для Djoser."""
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name', 'avatar'
        )

    def validate(self, data):
        if not data.get("avatar"):
            raise serializers.ValidationError("Аватар не предоставлен.")
        return data
