"""
Cấu hình Django cho dự án UITie.

Module này định nghĩa các cài đặt quan trọng cho môi trường dev:
- đọc biến môi trường qua .env để không commit secret vào git
- cấu hình kết nối SQL Server cho database legacy
- bật JWT authentication cho API REST
- kích hoạt CORS dev để React frontend có thể gọi API local
- sử dụng custom user model `authentication.Users`
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Đọc biến môi trường từ file .env để giữ credentials và cấu hình nhạy cảm
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Tại sao: Secret key dùng để sinh JWT, session và mã hóa dữ liệu nội bộ.
# Nếu lộ key thì attacker có thể forge token hoặc giải mã dữ liệu nhạy cảm.
SECRET_KEY = 'django-insecure-+z*r8%_0m(pgtpc8yrm@wa0y6mwzea(4znoxpc)d)@so6fslo6'

# SECURITY WARNING: don't run with debug turned on in production!
# Tại sao: DEBUG=True chỉ dùng trong dev để hiển thị traceback chi tiết.
# Production phải tắt để tránh lộ thông tin nội bộ và cấu trúc hệ thống.
DEBUG = True

# ALLOWED_HOSTS để giới hạn tên miền/host được phép truy cập app.
ALLOWED_HOSTS = []


# Application definition
# Tại sao: đăng ký app Django cần thiết cho admin, auth, session và REST API.
# Thêm corsheaders để cho phép frontend React dev truy cập API local.
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'apps.authentication',
    'apps.posts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'UITie_Python',                                 
        'USER': 'sa',                                    
        'PASSWORD': os.getenv('DB_PASSWORD', 'T@oLaPassWord123'),                  
        'HOST': '127.0.0.1',                             
        'PORT': '1433',                                  
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',    
            'extra_params': 'TrustServerCertificate=yes;', 
        },
    }
}

# Tại sao: cấu hình database liên kết app với SQL Server legacy.
# Sử dụng biến môi trường cho password để tránh lộ credentials trong source.


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Ho_Chi_Minh'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# ---- CẤU HÌNH THÊM CHO ĐỒ ÁN UITIE ----

# 1. Cho phép tất cả các nguồn (React Localhost) kết nối đến API trong giai đoạn dev
# Tại sao: frontend React chạy trên host/port khác, nên cần mở CORS để test local.
CORS_ALLOW_ALL_ORIGINS = True 

# 2. Định nghĩa REST Framework sử dụng JWT làm phương thức xác thực chính
# Tại sao: API backend dùng token-based auth để frontend gọi sạch hơn và tách biệt session.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

# 3. Cấu hình thời gian hết hạn của Token bảo mật
# Tại sao: cân bằng giữa trải nghiệm người dùng và bảo mật.
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),      # Token dùng trong 1 ngày
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # Refresh Token dùng trong 7 ngày
    'ROTATE_REFRESH_TOKENS': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,                       # Dùng chính Secret Key phía trên để mã hóa
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# 4. Sử dụng custom user model cho authentication app
# Tại sao: model `authentication.Users` chứa thêm role/status để phù hợp nghiệp vụ user management.
AUTH_USER_MODEL = 'authentication.Users'