# Generated by Django 4.2.17 on 2024-12-29 20:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="recipe",
            name="tags",
            field=models.ManyToManyField(
                help_text="Выберите теги рецепта",
                related_name="recipes",
                to="recipes.tag",
                verbose_name="Теги",
            ),
        ),
        migrations.DeleteModel(
            name="TagInRecipe",
        ),
    ]
