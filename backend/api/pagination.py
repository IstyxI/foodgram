from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Кастомный пагинатор."""

    page_size_query_param = "limit"


class PaginationForRecipes(PageNumberPagination):
    """Предназначен для пагинирования рецептов в подписках."""

    page_size = 3
