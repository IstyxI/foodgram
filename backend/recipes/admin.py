from django.contrib.admin import ModelAdmin, register

from .models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)


@register(Ingredient)
class IngredientAdmin(ModelAdmin):
    list_display = ("pk", "name", "measurement_unit")
    list_display_links = ["name",]
    search_fields = ("name", "name__istartswith")


@register(Recipe)
class RecipeAdmin(ModelAdmin):
    list_display = (
        "pk", "name", "author",
        "get_favorites", "get_tags", "created"
    )
    list_display_links = ["name", "author"]
    list_filter = ("tags",)
    search_fields = ("name", "name__istartswith")

    def get_queryset(self, request):
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "tags", "ingredients"
        )
        return queryset

    def get_favorites(self, obj):
        return obj.favorites.count()

    def get_tags(self, obj):
        return "\n".join(obj.tags.values_list("name", flat=True))


@register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("pk", "name", "slug")
    list_display_links = ["name",]
    search_fields = ("name", "name__istartswith")
    prepopulated_fields = {"slug": ("name",)}


@register(ShoppingCart)
class ShoppingCartAdmin(ModelAdmin):
    list_display = ("pk", "user", "recipe")
    list_display_links = ["user",]


@register(Follow)
class FollowAdmin(ModelAdmin):
    list_display = ("pk", "user", "author")
    search_fields = (
        "user__username", "author__username",
        "user__username__istartswith", "author__username__istartswith"
    )
    list_display_links = ["user",]

    def get_queryset(self, request):
        queryset = Follow.objects.select_related("author")
        return queryset


@register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("pk", "user", "recipe")
    list_display_links = ["user",]

    def get_queryset(self, request):
        queryset = Favorite.objects.select_related("recipe")
        return queryset
