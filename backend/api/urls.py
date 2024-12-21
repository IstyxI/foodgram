from api.views import (
    IngredientsViewSet,
    RecipeViewSet,
    TagsViewSet,
    UserCreateViewSet,
)
from django.urls import include, path
from rest_framework.routers import DefaultRouter

app_name = "api"

router = DefaultRouter()
router.register("tags", TagsViewSet, "tags")
router.register("ingredients", IngredientsViewSet, "ingredients")
router.register("recipes", RecipeViewSet, "recipes")
router.register("users", UserCreateViewSet, "users")

urlpatterns = (
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
)