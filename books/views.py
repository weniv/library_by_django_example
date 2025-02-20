from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import librarian_required
from books.forms import BookForm, LoanForm, ReservationForm
from books.models import Book, Loan, Reservation
from django.db import models
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.conf import settings
import logging
# Create your views here.
logger = logging.getLogger(__name__)

def book_list(request):
    """도서 목록 및 검색"""
    query = request.GET.get('query', '')
    use_cache = request.GET.get('cache', 'true') == 'true'
    
    start_time = timezone.now()
    
    if query:
        books = list(Book.objects.filter(
            models.Q(title__icontains=query) |
            models.Q(author__icontains=query) |
            models.Q(isbn__icontains=query)
        ))
        cache_status = "검색어가 있어 캐시 미사용"
    else:
        cache_key = 'all_books'
        
        if use_cache:
            books = cache.get(cache_key)
            if books is None:
                # QuerySet을 리스트로 변환하여 실제 데이터를 캐시에 저장
                books = list(Book.objects.all())
                cache.set(cache_key, books, settings.CACHE_TTL)
                cache_status = "캐시 미스 (DB 조회)"
            else:
                cache_status = "캐시 히트"
        else:
            # QuerySet을 리스트로 변환하여 실제 데이터를 가져옴
            books = list(Book.objects.all())
            cache_status = "캐시 미사용"
    
    end_time = timezone.now()
    elapsed_time = end_time - start_time
    
    # books가 이미 리스트이므로 len() 사용
    logger.warning(f'도서 목록 조회 성능: '
                  f'캐시상태={cache_status}, '
                  f'도서수={len(books)}, '
                  f'소요시간={elapsed_time.total_seconds():.4f}초')
    
    return render(request, 'books/book_list.html', {
        'books': books,
        'query': query,
        'elapsed_time': elapsed_time.total_seconds(),
        'cache_status': cache_status,
        'use_cache': use_cache
    })


def book_detail(request, pk):
    """도서 상세 정보"""
    book = get_object_or_404(Book, pk=pk)  # 도서 조회
    # 도서 상세 정보 템플릿 렌더링
    return render(request, 'books/book_detail.html', {'book': book})


@librarian_required  # 사서 권한 데코레이터
def book_create(request):
    """도서 등록 (사서 전용)"""
    if request.method == 'POST':  # POST 요청인 경우
        form = BookForm(request.POST)  # 폼 데이터 바인딩
        if form.is_valid():  # 폼 데이터 유효성 검사
            book = form.save(commit=False)  # 도서 정보 저장
            book.available_quantity = book.total_quantity  # 대출 가능 수량 초기화
            book.save()  # 도서 정보 저장
            messages.success(request, '도서가 등록되었습니다.')  # 성공 메시지
            return redirect('books:book-detail', pk=book.pk)  # 도서 상세 페이지로 이동
        else:
            messages.error(request, '도서 등록에 실패했습니다.')
            print(form.errors)
    else:
        form = BookForm()  # 폼 초기화
    # 도서 등록 폼 렌더링
    return render(request, 'books/book_form.html', {'form': form, 'title': '도서 등록'})


@librarian_required  # 사서 권한 데코레이터
def book_update(request, pk):
    """도서 수정 (사서 전용)"""
    book = get_object_or_404(Book, pk=pk)  # 도서 조회
    if request.method == 'POST':  # POST 요청인 경우
        form = BookForm(request.POST, instance=book)  # 폼 데이터 바인딩
        if form.is_valid():  # 폼 데이터 유효성 검사
            book = form.save()  # 도서 정보 저장
            messages.success(request, '도서가 수정되었습니다.')  # 성공 메시지
            return redirect('books:book-detail', pk=book.pk)  # 도서 상세 페이지로 이동
    else:
        form = BookForm(instance=book)  # 폼 초기화
    # 도서 수정 폼 렌더링
    return render(request, 'books/book_form.html', {'form': form, 'title': '도서 수정'})


@librarian_required  # 사서 권한 데코레이터
def book_delete(request, pk):
    """도서 삭제 (사서 전용)"""
    book = get_object_or_404(Book, pk=pk)  # 도서 조회
    if request.method == 'POST':  # POST 요청인 경우
        book.delete()  # 도서 삭제
        messages.success(request, '도서가 삭제되었습니다.')
        return redirect('books:book-list')  # 도서 목록 페이지로 이동
    # 도서 삭제 확인 페이지 렌더링
    return render(request, 'books/book_confirm_delete.html', {'book': book})


@login_required  # 로그인 여부 확인
def loan_create(request, book_id):
    """도서 대출 처리"""
    book = get_object_or_404(Book, pk=book_id)

    if request.method == 'POST':
        form = LoanForm(request.POST, user=request.user,
                        book=book)  # 폼 데이터 바인딩
        if form.is_valid():
            loan = form.save(commit=False)  # 대출 정보 저장
            loan.user = request.user
            loan.book = book
            loan.due_date = timezone.now() + timedelta(days=14)  # 14일 대출
            loan.save()

            # 도서 수량 감소
            book.decrease_quantity()
            messages.success(request, f'{book.title} 도서가 대출되었습니다. 반납일은 {loan.due_date.date()}입니다.')
            return redirect('books:loan-list')  # 대출 목록 페이지로 이동
    else:
        form = LoanForm(user=request.user, book=book)  # 폼 초기화

    return render(request, 'books/loan_form.html', {
        'form': form,
        'book': book
    })  # 대출 폼 렌더링


@login_required
def loan_list(request):
    """대출 목록 조회"""
    if request.user.is_librarian():  # 사서인 경우
        loans = Loan.objects.all().order_by('-loan_date')  # 모든 대출 목록 조회
    else:  # 일반 사용자인 경우
        loans = Loan.objects.filter(user=request.user).order_by(
            '-loan_date')  # 사용자의 대출 목록 조회

    return render(request, 'books/loan_list.html', {
        'loans': loans
    })


@login_required
def loan_return(request, loan_id):
    """도서 반납 처리"""
    loan = get_object_or_404(Loan, pk=loan_id)

    # 본인의 대출이거나 사서만 반납 가능
    if request.user != loan.user and not request.user.is_librarian():
        messages.error(request, '권한이 없습니다.')
        return redirect('books:loan-list')

    if request.method == 'POST':
        if loan.status == 'ACTIVE':
            loan.status = 'RETURNED'
            loan.returned_date = timezone.now()
            loan.save()

            # 도서 수량 증가
            loan.book.increase_quantity()

            # 예약자 확인 및 처리
            waiting_reservation = Reservation.objects.filter(
                book=loan.book,
                status='WAITING'
            ).order_by('reserved_date').first()

            if waiting_reservation:
                waiting_reservation.status = 'AVAILABLE'
                waiting_reservation.save()
                messages.success(
                    request,
                    '도서가 반납되었습니다. 예약자가 있어 예약자에게 우선권이 부여됩니다.'
                )
            else:
                messages.success(request, '도서가 반납되었습니다.')

        return redirect('books:loan-list')
    
    else:
        messages.error(request, '잘못된 접근입니다.')
        return redirect('books:loan-list')


@librarian_required
def loan_overdue_list(request):
    """연체 도서 목록 (사서용)"""
    overdue_loans = Loan.objects.filter(
        status='ACTIVE',  # 대출 중인 도서
        due_date__lt=timezone.now()  # 현재 시간보다 이전
    ).order_by('due_date')  # 반납일 기준으로 정렬

    return render(request, 'books/loan_list.html', {
        'loans': overdue_loans,
        'show_overdue': True
    })


@login_required  # 로그인 여부 확인
def reservation_create(request, book_id):
    """도서 예약"""
    book = get_object_or_404(Book, pk=book_id)

    if request.method == 'POST':  # POST 요청인 경우
        form = ReservationForm(request.POST, user=request.user, book=book)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.book = book
            reservation.expiry_date = timezone.now() + timedelta(days=1)  # 1일간 예약 유효
            reservation.save()

            messages.success(request, f'{book.title} 도서가 예약되었습니다.')
            return redirect('books:reservation-list')  # 예약 목록 페이지로 이동
    else:
        form = ReservationForm(user=request.user, book=book)

    return render(request, 'books/reservation_form.html', {
        'form': form,
        'book': book
    })


@login_required
def reservation_list(request):
    """예약 목록"""
    if request.user.is_librarian():  # 사서인 경우
        reservations = Reservation.objects.all().order_by('reserved_date')  # 모든 예약 목록 조회
    else:
        reservations = Reservation.objects.filter(
            user=request.user,
            status__in=['WAITING', 'AVAILABLE']  # 대기 중, 대출 가능한 예약만 조회
        ).order_by('reserved_date')

    return render(request, 'books/reservation_list.html', {
        'reservations': reservations
    })


@login_required
def reservation_cancel(request, reservation_id):
    """예약 취소"""
    reservation = get_object_or_404(Reservation, pk=reservation_id)

    if request.user != reservation.user and not request.user.is_librarian():  # 본인의 예약이거나 사서만 취소 가능
        messages.error(request, '권한이 없습니다.')
        return redirect('books:reservation-list')

    if request.method == 'POST':
        if reservation.status in ['WAITING', 'AVAILABLE']:  # 대기 중, 대출 가능한 경우에만 취소 가능
            reservation.status = 'CANCELLED'  # 예약 취소
            reservation.save()  # 예약 정보 저장
            messages.success(request, '예약이 취소되었습니다.')

        return redirect('books:reservation-list')  # 예약 목록 페이지로 이동
    
    else:
        messages.error(request, '잘못된 접근입니다.')
        return redirect('books:reservation-list')  # 예약 목록 페이지로 이동
