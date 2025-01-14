from django.contrib.admin import ModelAdmin, register
from django.db.models import Count

from .models import Favorite, Follow, Ingredient, Recipe, ShoppingCart, Tag


@register(Ingredient)
class IngredientAdmin(ModelAdmin):
    list_display = ("pk", "name", "measurement_unit")
    list_display_links = ("name", )
    search_fields = ("name", )


@register(Recipe)
class RecipeAdmin(ModelAdmin):
    list_display = (
        "pk", "name", "author",
        "favorites_count", "get_tags", "created"
    )
    list_display_links = ("name", "author")
    list_filter = ("tags", )
    search_fields = ("name", )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("author").prefetch_related(
            "tags", "ingredients"
        ).annotate(favorites_count=Count("favorites"))
        return queryset

    def favorites_count(self, obj):
        return obj.favorites_count

    def get_tags(self, obj):
        return "\n".join(obj.tags.values_list("name", flat=True))


@register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("pk", "name", "slug")
    list_display_links = ("name", )
    search_fields = ("name", )
    prepopulated_fields = {"slug": ("name",)}


@register(ShoppingCart)
class ShoppingCartAdmin(ModelAdmin):
    list_display = ("pk", "user", "recipe")
    list_display_links = ("user", )


@register(Follow)
class FollowAdmin(ModelAdmin):
    list_display = ("pk", "user", "author")
    search_fields = ("user__username", "author__username", )
    list_display_links = ("user", )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("author", "user")
        return queryset


@register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("pk", "user", "recipe")
    list_display_links = ("user__username", "recipe__name")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related("recipe", "user")
        return queryset
