from django.contrib.auth.tokens import default_token_generator
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.models import User
from users.serializers import UserCreateSerializer
from users.utils import send_confirmation_code

from .models import AmountOfIngredient, Cart, Favorite, Ingredient, Recipe, Tag
from .pagination import LimitPageNumberPagination
from .permissions import AdminOrReadOnly, OwnerUserOrReadOnly
from .serializers import IngredientSerializer, RecipeSerializer, TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (OwnerUserOrReadOnly,)
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitPageNumberPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        if request.method == 'GET':
            return self.add_obj(Favorite, request.user, pk)
        return self.delete_obj(Favorite, request.user, pk)

    @action(detail=True, methods=['get', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        if request.method == 'GET':
            return self.add_obj(Cart, request.user, pk)
        return self.delete_obj(Cart, request.user, pk)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        final_list = {}
        ingredients = AmountOfIngredient.objects.filter(
            recipe__cart__user=request.user).values_list(
            'ingredient__name', 'ingredient__measurement_unit',
            'amount')
        for item in ingredients:
            name = item[0]
            if name not in final_list:
                final_list[name] = {
                    'measurement_unit': item[1],
                    'amount': item[2]
                }
            else:
                final_list[name]['amount'] += item[2]


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AdminOrReadOnly,)
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ('^name',)


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AdminOrReadOnly,)
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class UserCreateViewSet(mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    """Вьюсет для создания обьектов класса User."""

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (AllowAny,)

    def create(self, request):
        """Создает объект User и отправляет пользователю код подтверждения."""
        serializer = UserCreateSerializer(data=request.data)
        if User.objects.filter(
            username=request.data.get('username'),
            email=request.data.get('email')
        ).first():
            user = get_object_or_404(
                User,
                username=request.data.get('username')
            )
            send_confirmation_code(
                email=request.data.get('email'),
                confirmation_code=user.confirmation_code
            )
            return Response(request.data, status=status.HTTP_200_OK)

        serializer.is_valid(raise_exception=True)
        try:
            user, _ = User.objects.get_or_create(**serializer.validated_data)

        except IntegrityError:
            return Response(
                {'error': 'Invalid request'},
                status=status.HTTP_400_BAD_REQUEST
            )

        confirmation_code = default_token_generator.make_token(user)
        send_confirmation_code(
            email=user.email,
            confirmation_code=confirmation_code
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
