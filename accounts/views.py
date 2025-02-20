from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import UserRegistrationForm, LoginForm

def register_view(request): # rqeuest: 요청 객체
    """회원가입 뷰"""
    if request.user.is_authenticated: # 로그인 상태인 경우
        return redirect('accounts:profile') # 프로필 페이지로 이동
        
    if request.method == 'POST': # POST 요청인 경우
        form = UserRegistrationForm(request.POST) # 회원가입 폼 생성
        if form.is_valid(): # 유효성 검사
            print(form)
            user = form.save() # 회원가입
            login(request, user) # 로그인
            messages.success(request, '회원가입이 완료되었습니다.') # 메시지 출력
            return redirect('accounts:profile') # 프로필 페이지로 이동
        else:
            print("Form errors:", form.errors)  # 에러 메시지 출력
    else: # GET 요청인 경우
        form = UserRegistrationForm() # 회원가입 폼 생성
    
    return render(request, 'accounts/register.html', {'form': form}) # 회원가입 페이지 렌더링

def login_view(request):
    """로그인 뷰"""
    if request.user.is_authenticated:
        print("User is already authenticated")
        return redirect(reverse_lazy('accounts:profile'))
        
    if request.method == 'POST':
        print("POST data received:", request.POST)  # POST 데이터 확인
        form = LoginForm(request, request.POST)
        if form.is_valid():
            print("Form is valid")
            user = form.get_user()
            print("User object:", user)  # 유저 객체 확인
            login(request, user)
            print("User logged in successfully")
            next_url = request.GET.get('next', reverse_lazy('accounts:profile'))
            print("Redirecting to:", next_url)
            return redirect(next_url)
        else:
            print("Form validation errors:", form.errors)  # 폼 에러 확인
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """로그아웃 뷰"""
    if request.method == 'POST':
        logout(request) # 로그아웃
        messages.success(request, '로그아웃되었습니다.') # 메시지 출력
        return redirect(reverse_lazy('accounts:login')) # 로그인 페이지로 이동

@login_required # 로그인 필요 이 데코레이터는 로그인이 필요한 경우에만 접근 가능하도록 설정
def profile_view(request):
    """프로필 뷰"""
    return render(request, 'accounts/profile.html', { # 프로필 페이지 렌더링
        'active_loans': request.user.get_active_loans(), # 현재 대출 중인 도서 목록
        'active_reservations': request.user.get_active_reservations() # 현재 예약 중인 도서 목록
    })