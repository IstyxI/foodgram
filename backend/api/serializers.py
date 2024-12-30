import base64

from django.core.files.base import ContentFile
from django.core.validators import RegexValidator

from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer

from recipes.models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)
from users.models import User


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для кодирования изображения в base64."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name="photo." + ext)

        return super().to_internal_value(data)


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
    """Сериализатор для модели User."""

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
        """Метод проверки подписки"""

        user = self.context.get("request").user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj.id).exists()


class CustomCreateUserSerializer(CustomUserSerializer):
    """Сериализатор для создания пользователя
    без проверки на подписку"""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True)

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
        """Метод проверки на добавление в избранное."""

        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Метод проверки на присутствие в корзине."""

        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class CreateIngredientsInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецептах"""

    id = serializers.IntegerField(required=True)
    amount = serializers.IntegerField(required=True)

    class Meta:
        model = IngredientInRecipe
        fields = ("id", "amount")

    @staticmethod
    def validate_amount(value):
        """Метод валидации количества"""

        if value < 1:
            raise serializers.ValidationError(
                "Количество ингредиента должно быть больше 0!"
            )
        return value


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""

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
        """Метод представления модели"""

        serializer = RecipeSerializer(
            instance, context={"request": self.context.get("request")}
        )
        return serializer.data

    def validate(self, data):
        """Метод валидации ингредиентов"""

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
        """Метод создания ингредиента"""
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
        """Метод добавления тега"""

        recipe.tags.set(tags)

    def create(self, validated_data):
        """Метод создания модели"""
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        user = self.context.get("request").user
        recipe = Recipe.objects.create(**validated_data, author=user)
        self.create_ingredients(ingredients, recipe)
        self.create_tags(tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Метод обновления модели"""

        if "ingredients" not in validated_data:
            raise serializers.ValidationError(
                "Поле ingredients обязательно для обновления!"
            )
        if "tags" not in validated_data:
            raise serializers.ValidationError(
                "Поле tags обязательно для обновления!"
            )

        IngredientInRecipe.objects.filter(recipe=instance).delete()

        self.create_ingredients(validated_data.pop("ingredients"), instance)
        self.create_tags(validated_data.pop("tags"), instance)

        return super().update(instance, validated_data)


class AdditionalForRecipeSerializer(serializers.ModelSerializer):
    """Дополнительный сериализатор для рецептов"""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(CustomUserSerializer):
    """Сериализатор для модели Follow."""

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
        """Метод для получения рецептов"""

        request = self.context.get("request")
        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get("recipes_limit", 10)
        if recipes_limit:
            recipes = recipes[: int(recipes_limit)]
        return ShortRecipeSerializer(recipes, many=True).data

    @staticmethod
    def get_recipes_count(obj):
        """Метод для получения количества рецептов"""

        return obj.recipes.count()


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецептов"""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class SubscriptionSerializer(serializers.Serializer):
    author_id = serializers.IntegerField(required=True)

    def validate_author_id(self, value):
        user = self.context["request"].user
        try:
            author = User.objects.get(id=value)
        except User.DoesNotExist:
            raise ValidationError("Автор не найден.")
        if user == author:
            raise ValidationError("Вы не можете подписаться на самого себя.")
        return author.id

    def create(self, validated_data):
        """Метод создания модели"""
        user = self.context.get("request").user
        author = User.objects.get(pk=validated_data["author_id"])
        return Follow.objects.create(user=user, author=author)


class FavoriteSerializer(serializers.Serializer):
    """Сериализатор для Избранных рецептов"""

    recipe_id = serializers.IntegerField(required=True)

    def create(self, validated_data):
        """Метод создания модели"""
        user = self.context.get("request").user
        recipe = Recipe.objects.get(pk=validated_data["recipe_id"])
        return Favorite.objects.create(user=user, recipe=recipe)
