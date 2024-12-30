import csv

from django.core.management.base import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    """Загружает теги базу из csv файла."""

    def handle(self, *args, **options):
        self.import_tags()

    def import_tags(self, file='tags.csv'):
        file_path = f'./data/{file}'
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                status, created = Tag.objects.update_or_create(
                    name=row[0],
                    slug=row[1]
                )
