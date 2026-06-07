"""Serializers cho ứng dụng xác thực.

Dùng để validate, transform dữ liệu người dùng giữa Django backend
và Frontend API, bao gồm đăng nhập, đăng ký, cập nhật hồ sơ.
"""

from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from apps.authentication.models import Users


class UserResponseSerializer(serializers.ModelSerializer):
    """
    Serializer cho response dữ liệu người dùng trả về Frontend.
    
    Chỉ expose các trường cơ bản cần thiết để giảm dung lượng response,
    bảo vệ thông tin nhạy cảm (password, token). Ép ID thành string
    để match với interface TypeScript của Frontend (id: string).
    """
    id = serializers.CharField(read_only=True) 

    class Meta:
        model = Users
        fields = ['id', 'full_name', 'email', 'role', 'status']


class LoginRequestSerializer(serializers.Serializer):
    """
    Serializer validate dữ liệu đăng nhập từ Frontend.
    
    Đảm bảo email có format hợp lệ (RFC 5321) và password không
    bị expose ra response (write_only=True). Là bước xác thực đầu tiên
    trước khi xử lý logic authentication.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserSaveSerializer(serializers.ModelSerializer):
    """
    Serializer validate và lưu dữ liệu người dùng (create/update).
    
    Kiểm soát trường nào được phép gửi lên từ Frontend. Password
    không bắt buộc khi sửa (cho phép admin chỉ cập nhật thông tin
    mà không thay đổi password).
    """
    class Meta:
        model = Users
        fields = ['email', 'password', 'full_name', 'role', 'status']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def create(self, validated_data):
        """
        Tạo người dùng mới với mã hóa mật khẩu.
        
        Luôn mã hóa password trước lưu để tuân theo quy tắc bảo mật:
        - Password không được lưu ở dạng plain text
        - Sử dụng PBKDF2 hash algorithm của Django
        
        Args:
            validated_data: Dữ liệu đã validate từ Frontend
            
        Returns:
            Users: Instance người dùng vừa tạo
        """
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Cập nhật thông tin người dùng với xử lý đặc biệt cho password.
        
        Cho phép 2 trường hợp:
        - Nếu Admin gửi password mới -> Mã hóa và cập nhật
        - Nếu admin không gửi password (trường trống) -> Giữ nguyên mật khẩu cũ
        
        Điều này tránh tình trạng vô tình reset password thành rỗng.
        
        Args:
            instance: Người dùng hiện tại
            validated_data: Dữ liệu cập nhật
            
        Returns:
            Users: Instance sau khi cập nhật
        """
        if 'password' in validated_data and validated_data['password']:
            validated_data['password'] = make_password(validated_data['password'])
        else:
            validated_data.pop('password', None)
        return super().update(instance, validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer cho trang hồ sơ cá nhân (Profile page).
    
    Expose toàn bộ thông tin chi tiết của người dùng kèm các metric
    về mạng xã hội (followers, following). Hỗ trợ so sánh độ tương
    thích (match_score) giữa người xem và chủ profile để tính năng gợi ý.
    """
    id = serializers.CharField(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = [
            'id', 'email', 'full_name', 'mssv', 'phone_number', 
            'role', 'status', 'faculty', 'class_name', 'academic_year', 
            'created_at', 'updated_at', 'followers_count', 'following_count', 'is_following', 'is_me', 'match_score'
        ]

    def get_followers_count(self, obj):
        """Đếm số người theo dõi người dùng này."""
        from apps.posts.models import Follows
        return Follows.objects.filter(following=obj).count()

    def get_following_count(self, obj):
        """Đếm số người mà người dùng này đang theo dõi."""
        from apps.posts.models import Follows
        return Follows.objects.filter(follower=obj).count()
        
    def get_is_following(self, obj):
        """
        Kiểm tra người xem có đang theo dõi chủ profile hay không.
        
        Trường này giúp Frontend biết có nên hiển thị nút "Follow"
        hay "Unfollow". Luôn trả về False nếu xem profile của chính mình.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user == obj:
                return False
            from apps.posts.models import Follows
            return Follows.objects.filter(follower=request.user, following=obj).exists()
        return False

    def get_is_me(self, obj):
        """
        Kiểm tra xem profile này có phải của chính người xem hay không.
        
        Frontend dùng để quyết định hiển thị nút "Edit Profile" hay
        nút "Follow". Chỉ owner mới được chỉnh sửa profile của mình.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj
        return False

    def get_match_score(self, obj):
        """
        Lấy điểm tương thích giữa người xem và chủ profile.
        
        Giá trị này được tính toán ở view (sử dụng annotate) dựa trên
        các tiêu chí như chung faculty, academic_year, quan tâm chung,...
        Trả về 0 nếu view không tính toán (safe fallback).
        """
        return getattr(obj, 'match_score', 0)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cập nhật profile cho user thường (không phải admin).
    
    Giới hạn chỉ cho phép sửa thông tin cá nhân, không cho phép
    sửa email (định danh duy nhất), role, status. Đảm bảo an toàn
    dữ liệu và ngăn user nâng cao quyền cho mình.
    """
    class Meta:
        model = Users
        fields = ['full_name', 'phone_number', 'faculty', 'class_name', 'academic_year']