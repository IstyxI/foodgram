import django_filters
from django_filters import rest_framework
from django_filters.rest_framework import FilterSet

from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(FilterSet):
    """Поиск по названию ингредиента."""

    name = rest_framework.CharFilter(lookup_expr="istartswith")

    class Meta:
        model = Ingredient
        fields = ("name",)


class RecipeFilter(django_filters.FilterSet):
    """Фильтр для отображения избранного и списка покупок"""

    tags = django_filters.filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name="tags__slug",
        to_field_name="slug"
    )
    is_favorited = django_filters.filters.NumberFilter(
        method="is_recipe_in_favorites_filter"
    )
    is_in_shopping_cart = django_filters.filters.NumberFilter(
        method="is_recipe_in_shoppingcart_filter"
    )
    author = django_filters.filters.AllValuesMultipleFilter(
        field_name='author__id'
    )

    class Meta:
        model = Recipe
        fields = ("tags", "author", "is_favorited", "is_in_shopping_cart")

    def is_recipe_in_favorites_filter(self, queryset, name, value):
        if value == 1:
            user = self.request.user
            return queryset.filter(favorites__user_id=user.id)
        return queryset

    def is_recipe_in_shoppingcart_filter(self, queryset, name, value):
        if value == 1:
            user = self.request.user
            return queryset.filter(shopping_recipe__user_id=user.id)
        return queryset
