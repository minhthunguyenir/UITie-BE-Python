from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from apps.authentication.models import Users
from apps.authentication.serializers import LoginRequestSerializer, UserResponseSerializer

class LoginAPIView(APIView):
    def post(self, request):
        # 1. Validate dữ liệu đầu vào (LoginRequest)
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            # 2. Tìm người dùng trong Database bằng Email
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response(
                {"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Kiểm tra trạng thái tài khoản
        if user.status == 'Locked':
            return Response(
                {"detail": f"Tài khoản đã bị khóa! Lý do: {user.status_reason or 'Không có'}"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.status == 'Inactive':
            return Response(
                {"detail": "Tài khoản chưa được kích hoạt!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. Kiểm tra mật khẩu (Django tự động check được cả hash Bcrypt của Laravel nếu cấu hình chuẩn)
        if not check_password(password, user.password):
            return Response(
                {"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 5. Khởi tạo Token JWT bằng SimpleJWT
        refresh = RefreshToken.for_user(user)
        
        # 6. Đóng gói dữ liệu trả về KHỚP 100% với LoginResponse bên Frontend
        return Response({
            "data": {
                "user": UserResponseSerializer(user).data,
                "token": str(refresh.access_token)
            }
        }, status=status.HTTP_200_OK)