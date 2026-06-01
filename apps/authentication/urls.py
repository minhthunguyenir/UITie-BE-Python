# apps/authentication/urls.py
from django.urls import path
from apps.authentication.views import LoginAPIView, UserListAPIView, UserDetailAPIView

urlpatterns = [
    # 1. Đường dẫn Đăng nhập
    path('login', LoginAPIView.as_view(), name='login_api'),
    
    # 2. Đường dẫn Xem danh sách & Thêm tài khoản (Không có ID)
    path('super-admin/user', UserListAPIView.as_view(), name='super_admin_user_api'),
    path('admin/user', UserListAPIView.as_view(), name='admin_user_api'),
    
    # 3. Đường dẫn Chỉnh sửa & Khóa tài khoản
    path('super-admin/user/<int:pk>', UserDetailAPIView.as_view(), name='super_admin_user_detail_api'),
    path('admin/user/<int:pk>', UserDetailAPIView.as_view(), name='admin_user_detail_api'),
]