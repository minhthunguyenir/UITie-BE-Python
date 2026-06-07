"""
Cấu hình ứng dụng Authentication (xác thực) cho Django.

Ứng dụng này quản lý toàn bộ logic xác thực người dùng, bao gồm
đăng nhập, đăng ký, quản lý phiên làm việc, và phân quyền.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """
    Cấu hình ứng dụng Django cho module xác thực.
    
    Đảm bảo Django nhận diện và tải đúng ứng dụng authentication
    với các mô hình, views, serializers, và URLs liên quan.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Xác thực và quản lý người dùng'
