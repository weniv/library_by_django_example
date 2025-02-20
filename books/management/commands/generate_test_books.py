# books/generate_test_books.py
from django.core.management.base import BaseCommand
from books.models import Book
from django.utils import timezone

class Command(BaseCommand):
    help = '테스트용 도서 데이터 생성'

    def add_arguments(self, parser):
        parser.add_argument('total', type=int, help='생성할 도서 수')

    def handle(self, *args, **kwargs):
        total = kwargs['total']
        
        for i in range(total):
            Book.objects.create(
                title=f'테스트 도서 {i+1}',
                author=f'저자 {i+1}',
                isbn = str(9780000000000 + i)[:13],
                publisher=f'출판사 {i+1}',
                total_quantity=10,
                available_quantity=10
            )
            if (i + 1) % 100 == 0:
                self.stdout.write(f'{i+1}개 도서 생성 완료')

        self.stdout.write(self.style.SUCCESS(f'총 {total}개의 테스트 도서가 생성되었습니다.'))