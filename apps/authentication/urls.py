from django.urls import path
from apps.authentication.views import LoginAPIView, UserListAPIView

urlpatterns = [
    # Định nghĩa cái đuôi của api đăng nhập
    path('login', LoginAPIView.as_view(), name='login_api'),
    
    # Tuyến đường dành cho Super Admin
    path('super-admin/user', UserListAPIView.as_view(), name='super_admin_user_api'),
    
    # Tuyến đường dành cho Admin thường
    path('admin/user', UserListAPIView.as_view(), name='admin_user_api'),
]