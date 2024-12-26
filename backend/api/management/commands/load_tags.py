import csv

from api.models import Tag
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Загружает теги базу из csv файла."""

    def handle(self, *args, **options):
        self.import_tags()
        print('Загрузка тегов для базы данных завершена.')

    def import_tags(self, file='tags.csv'):
        print(f'Загрузка {file}...')
        file_path = f'./data/{file}'
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                status, created = Tag.objects.update_or_create(
                    name=row[0],
                    slug=row[1]
                )
