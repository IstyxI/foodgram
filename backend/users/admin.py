from django.contrib.admin import register
from django.contrib.auth.admin import UserAdmin

from .models import User


@register(User)
class MyUserAdmin(UserAdmin):
    list_display = (
        "pk", "username", "email",
        "first_name", "last_name", "password"
    )
    list_display_links = ("username", )
    search_fields = ("username", "email", "first_name", "last_name")
