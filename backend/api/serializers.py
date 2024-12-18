from rest_framework import serializers

from .models import Recipe, Ingredient, AmountOfIngredient, Tag


class RecipeSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'title', 'description', 'author', 'image',
            'ingredients', 'tags', 'cook_time'
        )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('name', 'unit_of_measurement')


class AmountOfIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmountOfIngredient
        fields = ('ingredient', 'recipe', 'amount')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('name', 'slug')
