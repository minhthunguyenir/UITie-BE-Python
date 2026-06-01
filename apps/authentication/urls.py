# apps/authentication/urls.py
from django.urls import path
from apps.authentication.views import LoginAPIView, UserListAPIView, UserDetailAPIView
from apps.authentication.views import LoginAPIView, UserListAPIView, UserDetailAPIView, UserLockAPIView, UserUnlockAPIView

urlpatterns = [
    # 1. Đường dẫn Đăng nhập
    path('login', LoginAPIView.as_view(), name='login_api'),
    
    # 2. Đường dẫn Xem danh sách & Thêm tài khoản (Không có ID)
    path('super-admin/user', UserListAPIView.as_view(), name='super_admin_user_api'),
    path('admin/user', UserListAPIView.as_view(), name='admin_user_api'),
    
    # 3. Đường dẫn Chỉnh sửa & Khóa tài khoản
    path('super-admin/user/<int:pk>', UserDetailAPIView.as_view(), name='super_admin_user_detail_api'),
    path('admin/user/<int:pk>', UserDetailAPIView.as_view(), name='admin_user_detail_api'),

    # 4. Đuờng dẫn khóa tài khoản (chỉ cập nhật status thành 'Locked')
    path('super-admin/user/<int:pk>/lock', UserLockAPIView.as_view(), name='super_admin_user_lock_api'),
    path('admin/user/<int:pk>/lock', UserLockAPIView.as_view(), name='admin_user_lock_api'),

    # 5. Đường dẫn mở khóa tài khoản (chỉ cập nhật status thành 'Active')
    path('super-admin/user/<int:pk>/unlock', UserUnlockAPIView.as_view(), name='super_admin_user_unlock_api'),
    path('admin/user/<int:pk>/unlock', UserUnlockAPIView.as_view(), name='admin_user_unlock_api'),
]