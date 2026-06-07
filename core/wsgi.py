"""
WSGI config cho dự án UITie.

Module này cấu hình entry point WSGI để app Django có thể chạy
trên production server như Gunicorn hoặc uWSGI.

Tại sao cần file này:
- Nó đặt biến môi trường `DJANGO_SETTINGS_MODULE` cho Django biết file settings.
- Nó khởi tạo callable `application` để server WSGI có thể gọi vào.
- Giữ logic này riêng giúp tách rõ deployment layer với ứng dụng.
"""

import os

from django.core.wsgi import get_wsgi_application

# Thiết lập biến môi trường Settings trước khi khởi tạo Django application.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Callable WSGI được server như Gunicorn/uWSGI sử dụng để phục vụ Django.
application = get_wsgi_application()
