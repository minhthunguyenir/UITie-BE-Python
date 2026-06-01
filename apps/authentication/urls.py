from django.urls import path
from apps.authentication.views import LoginAPIView

urlpatterns = [
    # Định nghĩa cái đuôi của api đăng nhập
    path('login', LoginAPIView.as_view(), name='login_api'),
]