from django.contrib.auth.hashers import make_password
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

class UserSaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        # Các trường dữ liệu mà Form Frontend sẽ gửi lên khi Thêm hoặc Sửa
        fields = ['email', 'password', 'full_name', 'role', 'status']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False} # Giữ bí mật password, không bắt buộc truyền lúc Sửa
        }

    def create(self, validated_data):
        # 🛠️ MẠ SÁT BẢO MẬT: Mã hóa mật khẩu trước khi lưu khi TẠO MỚI
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Nếu lúc SỬA Admin có nhập mật khẩu mới -> Mã hóa luôn, nếu trống -> Giữ nguyên mk cũ
        if 'password' in validated_data and validated_data['password']:
            validated_data['password'] = make_password(validated_data['password'])
        else:
            validated_data.pop('password', None) # Không sửa mật khẩu nếu FE không truyền lên
        return super().update(instance, validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer dùng cho trang cá nhân (Profile) với nhiều thông tin chi tiết hơn"""
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
        from apps.posts.models import Follows
        return Follows.objects.filter(following=obj).count()

    def get_following_count(self, obj):
        from apps.posts.models import Follows
        return Follows.objects.filter(follower=obj).count()
        
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user == obj:
                return False
            from apps.posts.models import Follows
            return Follows.objects.filter(follower=request.user, following=obj).exists()
        return False

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj
        return False

    def get_match_score(self, obj):
        # Lấy giá trị match_score được annotate từ view, nếu không có thì trả về 0 an toàn
        return getattr(obj, 'match_score', 0)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer dùng riêng cho việc cập nhật Profile (giới hạn các trường được phép sửa)"""
    class Meta:
        model = Users
        fields = ['full_name', 'phone_number', 'faculty', 'class_name', 'academic_year']