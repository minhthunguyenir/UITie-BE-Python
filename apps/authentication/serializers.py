from rest_framework import serializers
from apps.authentication.models import Users

class UserResponseSerializer(serializers.ModelSerializer):
    """Serializer ép đúng kiểu dữ liệu cho object 'user' bên Frontend"""
    # Ép ID thành chuỗi (string) vì interface User quy định id: string
    id = serializers.CharField(read_only=True) 

    class Meta:
        model = Users
        fields = ['id', 'full_name', 'email', 'role', 'status']

class LoginRequestSerializer(serializers.Serializer):
    """Serializer bắt đúng cấu trúc LoginRequest từ Frontend gửi lên"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)