"""
Router gốc cho dự án UITie.

Danh sách `urlpatterns` ánh xạ các URL tới các view cụ thể. Đây là router gốc; các app nhỏ sẽ include routing nội bộ của chúng.
Lưu ý:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

# URL patterns cấp cao của dự án:
# - admin/ để truy cập Django admin panel.
# - api/ để chuyển tiếp các request API tới app authentication.
#
# Tại sao tách kiểu này:
# - Giữ router gốc đơn giản, app-level routing do từng app quản lý.
# - Dễ mở rộng khi thêm app mới mà không phải sửa core/urls.py nhiều.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.authentication.urls')),
]
