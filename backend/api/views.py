from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)
from recipes.permissions import IsAuthorOrReadOnly
from users.models import User

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .serializers import (
    CreateRecipeSerializer, CustomUserSerializer, DjoserCustomUserSerializer,
    FavoriteSerializer, FollowSerializer, IngredientSerializer,
    RecipeSerializer, ShoppingCartSerializer, ShortRecipeSerializer,
    SubscriptionSerializer, TagSerializer,
)


class TagViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Вьюсет работы с обьектами класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с обьектами класса Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ("^name",)
    pagination_class = None


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с обьектами класса User и подписки на авторов."""

    queryset = User.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination
    serializer_class = CustomUserSerializer

    def perform_update(self, serializer):
        """Метод для сохранения частичных данных."""
        if self.action == "me_avatar" and self.request.method == "PUT":
            user = self.request.user
            serializer = DjoserCustomUserSerializer(
                user,
                data=self.request.data,
                partial=True,
                context={'request': self.request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            super().perform_update(serializer)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(IsAuthenticated,),
        url_path="me",
        url_name="me",
    )
    def me(self, request):
        """Метод для получения информации о текущем пользователе."""
        serializer = self.serializer_class(
            request.user, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=("put", "delete"),
        permission_classes=(IsAuthenticated,),
        url_path="me/avatar",
        url_name="me-avatar",
    )
    def me_avatar(self, request):
        """Метод для обновления и удаления аватара текущего пользователя."""
        user = request.user
        if request.method == "PUT":
            avatar = request.data.get("avatar")
            serializer = DjoserCustomUserSerializer(
                user, data={'avatar': avatar},
                context={'request': request}
            )
            self.perform_update(serializer)
            return Response(
                {"avatar": user.avatar.url if user.avatar else None},
                status=status.HTTP_200_OK,
            )

        if request.method == "DELETE":
            if user.avatar:
                serializer = CustomUserSerializer(
                    user, context={'request': request}
                )
                serializer.fields['avatar'].delete(user, save=True)
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "У пользователя нет аватара"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(IsAuthenticated,),
        url_path="subscriptions",
        url_name="subscriptions",
    )
    def subscriptions(self, request):
        """Метод для создания страницы подписок."""
        queryset = User.objects.filter(
            follower__user=self.request.user
        ).annotate(recipes_count=Count("recipes"))
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(IsAuthenticated,),
        url_path="subscribe",
        url_name="subscribe",
    )
    def subscribe(self, request, id):
        """Метод для управления подписками."""
        user = request.user
        author = get_object_or_404(
            User.objects.annotate(recipes_count=Count("recipes")), pk=id
        )
        if request.method == "POST":
            data = {
                "user": request.user.id,
                "author": id
            }
            serializer = SubscriptionSerializer(
                data=data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user, author=author)
            serializer = FollowSerializer(
                author, context={"request": request}, many=False
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Follow.objects.filter(user=user, author=author).delete()
        if deleted:
            return Response(
                f"Вы отписались от {author}", status=status.HTTP_204_NO_CONTENT
            )
        return Response(
            f"Вы не подписаны на {author}", status=status.HTTP_400_BAD_REQUEST
        )


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для обработки запросов, связанных с рецептами."""

    pagination_class = CustomPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Метод для фильтрации рецептов по тегам."""
        return Recipe.objects.select_related("author").prefetch_related(
            "tags", "ingredients"
        )

    def get_serializer_class(self):
        """Метод для вызова определенного сериализатора."""
        if self.action in ("list", "retrieve"):
            return RecipeSerializer
        elif self.action in ("create", "partial_update"):
            return CreateRecipeSerializer

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        recipe = self.get_object()
        link = request.build_absolute_uri(f"/s/{recipe.short_url}")
        return Response({"short-link": link})

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(IsAuthenticated,),
        url_path="favorite",
        url_name="favorite",
    )
    def favorite(self, request, pk):
        """Метод для управления избранными подписками."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == "POST":
            serializer = FavoriteSerializer(
                data={"recipe_id": pk}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            obj = Favorite.objects.filter(user=user, recipe=recipe).delete()
            if obj != (0, {}):
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"errors": f'В избранном нет рецепта "{recipe.name}"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(IsAuthenticated,),
        url_path="shopping_cart",
        url_name="shopping_cart",
    )
    def shopping_cart(self, request, pk):
        """Метод для управления списком покупок."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == "POST":
            serializer = ShoppingCartSerializer(
                data={"recipe_id": pk}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            obj = ShoppingCart.objects.filter(
                user=user, recipe__id=pk
            ).delete()
            if obj != (0, {}):
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {
                    "errors": f'Нельзя удалить рецепт - "{recipe.name}", '
                    f"которого нет в списке покупок "
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def ingredients_to_txt(ingredients):
        """Метод для объединения ингредиентов в список для загрузки."""
        shopping_list = ""
        for ingredient in ingredients:
            shopping_list += (
                f"{ingredient['ingredient__name']}  - "
                f"{ingredient['sum']}"
                f"({ingredient['ingredient__measurement_unit']})\n"
            )
        return shopping_list

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(IsAuthenticated,),
        url_path="download_shopping_cart",
        url_name="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Загрузка ингредиентов и их количества для выбранных рецептов."""
        ingredients = (
            IngredientInRecipe.objects.filter(
                recipe__shopping_recipe__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(sum=Sum("amount"))
        )
        shopping_list = self.ingredients_to_txt(ingredients)
        return HttpResponse(shopping_list, content_type="text/plain")


def short_link_redirect(request, short_url):
    """Редирект по короткой ссылке."""
    recipe = get_object_or_404(Recipe, short_url=short_url)
    return redirect("api:recipes-detail", pk=recipe.id)
