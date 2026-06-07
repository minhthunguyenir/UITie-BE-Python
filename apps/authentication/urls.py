# apps/authentication/urls.py
from django.urls import include, path
from apps.authentication.views import LoginAPIView, UserListAPIView, UserDetailAPIView
from apps.authentication.views import LoginAPIView, UserListAPIView, UserDetailAPIView, UserLockAPIView, UserUnlockAPIView, UserProfileAPIView, UserFollowAPIView
from apps.posts.views import PostAdminListAPIView, PostValidateAPIView

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

    # 6. Đường dẫn lấy danh sách bài viết dành cho Admin/Super Admin
    path('super-admin/post', PostAdminListAPIView.as_view(), name='super_admin_post_api'),
    path('admin/post', PostAdminListAPIView.as_view(), name='admin_post_api'),

    # 7. Tuyến đường Lấy danh sách bài viết
    path('super-admin/post', PostAdminListAPIView.as_view(), name='super_admin_post_api'),
    path('admin/post', PostAdminListAPIView.as_view(), name='admin_post_api'),
    
    # 8. ĐƯỜNG DẪN KIỂM DUYỆT BÀI VIẾT
    path('super-admin/post/<int:pk>/validate', PostValidateAPIView.as_view(), name='super_admin_post_validate_api'),
    path('admin/post/<int:pk>/validate', PostValidateAPIView.as_view(), name='admin_post_validate_api'),

    # 9. Profile & Follow
    path('profile', UserProfileAPIView.as_view(), name='profile_current_api'),
    path('profile/<int:pk>', UserProfileAPIView.as_view(), name='profile_detail_api'),
    path('profile/<int:pk>/follow', UserFollowAPIView.as_view(), name='user_follow_api'),

    # 10.
    path('posts/', include('apps.posts.urls')),
]