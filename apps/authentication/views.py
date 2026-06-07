from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from apps.authentication.models import Users
from apps.authentication.serializers import LoginRequestSerializer, UserResponseSerializer
from apps.authentication.serializers import UserResponseSerializer, UserSaveSerializer, UserProfileSerializer, ProfileUpdateSerializer
from django.utils import timezone

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

class UserListAPIView(APIView):
    # Khai báo bắt buộc phải đăng nhập và truyền Token JWT ở Header thì mới nói chuyện tiếp
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. PHÂN QUYỀN: Kiểm tra xem người đang gọi API có phải là Admin không
        # (request.user lúc này chính là đối tượng User đang đăng nhập dựa theo Token gửi lên)
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response(
                {"detail": "Bạn không có quyền truy cập tính năng này!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. LẤY DỮ LIỆU: Lấy toàn bộ danh sách người dùng trong hệ thống
        users = Users.objects.all().order_by('-id') # Sắp xếp user mới tạo lên đầu danh sách

        # 3. SERIALIZE: Ép đống dữ liệu này qua Serializer (thêm many=True vì đây là một danh sách)
        serializer = UserResponseSerializer(users, many=True)

        # 4. ĐÓNG GÓI: Bọc trong key "data" để match với Frontend Laravel cũ
        return Response({
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        # Chốt chặn 1: Vẫn cấm quyền Student tuyệt đối không cho tạo tài khoản
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response(
                {"detail": "Bạn không có quyền thực hiện hành động này!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 🛠️ CHỐT CHẶN 2 (CHUẨN SRS): Kiểm tra phân cấp quyền của Admin thường
        if request.user.role == 'Admin':
            role_muon_tao = request.data.get('role')
            # Nếu Admin thường muốn tạo tài khoản Admin hoặc Super Admin -> Chặn ngay
            if role_muon_tao in ['Super Admin', 'Admin']:
                return Response(
                    {"detail": "Tài khoản Admin thường chỉ được phép tạo tài khoản cho Student"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        # ---- Nếu vượt qua các chốt chặn trên an toàn -> Tiến hành tạo tài khoản ----
        serializer = UserSaveSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "data": UserResponseSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserDetailAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # 1. PHÂN QUYỀN CHUNG: Chỉ Admin/Super Admin mới được vào phòng sửa
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        # 2. TÌM USER: Check xem cái ID (pk) cần sửa có tồn tại dưới DB không
        try:
            user_to_update = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        # 3. KIỂM TRA QUYỀN NÂNG CAO (Bảo vệ tuyệt đối theo SRS):
        if request.user.role == 'Admin':
            # - Admin thường KHÔNG ĐƯỢC phép đụng vào / sửa đổi tài khoản của Admin khác hoặc Super Admin
            if user_to_update.role in ['Super Admin', 'Admin']:
                return Response(
                    {"detail": "Tài khoản Admin thường không có quyền chỉnh sửa tài khoản cấp cao khác!"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            # - Admin thường nếu cố tình đổi role của user khác thành Admin/Super Admin cũng bị block luôn
            role_moi = request.data.get('role')
            if role_moi in ['Super Admin', 'Admin']:
                return Response(
                    {"detail": "Admin thường không thể nâng cấp tài khoản lên quyền Admin/Super Admin!"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        # 4. TIẾN HÀNH CẬP NHẬT: Dùng partial=True để FE chỉ cần gửi các trường thay đổi (ví dụ: gửi mỗi status để khóa)
        serializer = UserSaveSerializer(user_to_update, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({
                "data": UserResponseSerializer(updated_user).data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        try:
            user = Users.objects.get(pk=pk) if pk else request.user
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng!"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        
    def put(self, request, pk=None):
        # Chặn nếu user cố tình truyền id người khác để sửa
        if pk and str(pk) != str(request.user.id):
            return Response({"detail": "Bạn không có quyền chỉnh sửa hồ sơ của người khác!"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({
                "data": UserProfileSerializer(updated_user, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserFollowAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            target_user = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng!"}, status=status.HTTP_404_NOT_FOUND)
            
        if target_user == request.user:
            return Response({"detail": "Bạn không thể tự theo dõi chính mình!"}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.posts.models import Follows
        follow = Follows.objects.filter(follower=request.user, following=target_user).first()
        
        if follow:
            follow.delete()
            return Response({"data": {"detail": "Đã bỏ theo dõi", "is_following": False}}, status=status.HTTP_200_OK)
        else:
            Follows.objects.create(follower=request.user, following=target_user, created_at=timezone.now(), updated_at=timezone.now())
            return Response({"data": {"detail": "Đã theo dõi", "is_following": True}}, status=status.HTTP_200_OK)
    
class UserLockAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # 1. PHÂN QUYỀN CHUNG: Chỉ Admin/Super Admin mới được quyền khóa người khác
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        # 2. TÌM USER: Check xem tài khoản cần khóa có tồn tại không
        try:
            user_to_lock = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        # 3. KIỂM TRA QUYỀN NÂNG CAO (Theo SRS): Admin thường không được khóa Admin khác hoặc Super Admin
        if request.user.role == 'Admin' and user_to_lock.role in ['Super Admin', 'Admin']:
            return Response(
                {"detail": "Tài khoản Admin thường không có quyền khóa tài khoản cấp cao khác!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. TIẾN HÀNH KHÓA: Ép trạng thái thành 'Locked'
        # Đồng thời lấy toàn bộ dữ liệu FE gửi lên (bao gồm cả lý do khóa nhập tay nếu có)
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['status'] = 'Locked'

        # Dùng Serializer để cập nhật an toàn vào Database
        serializer = UserSaveSerializer(user_to_lock, data=data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({
                "data": UserResponseSerializer(updated_user).data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserUnlockAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # 1. PHÂN QUYỀN: Chỉ Admin/Super Admin mới được quyền mở khóa
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        # 2. TÌM USER: Check xem tài khoản cần mở khóa có tồn tại không
        try:
            user_to_unlock = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        # 3. KIỂM TRA QUYỀN NÂNG CAO (Theo SRS): Admin thường không được can thiệp tài khoản cấp cao
        if request.user.role == 'Admin' and user_to_unlock.role in ['Super Admin', 'Admin']:
            return Response(
                {"detail": "Tài khoản Admin thường không có quyền mở khóa tài khoản cấp cao khác!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. TIẾN HÀNH MỞ KHÓA: Ép trạng thái quay trở lại 'Active'
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['status'] = 'Active'

        # Lưu cập nhật vào Database SQL Server
        serializer = UserSaveSerializer(user_to_unlock, data=data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({
                "data": UserResponseSerializer(updated_user).data
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        if keyword:
            from django.db.models import Q
            users = Users.objects.filter(
                Q(full_name__icontains=keyword) | 
                Q(email__icontains=keyword) |
                Q(mssv__icontains=keyword)
            ).order_by('-id')
        else:
            users = Users.objects.none()
            
        serializer = UserResponseSerializer(users, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

class UserSuggestedFollowsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from apps.posts.models import Follows
        from django.db.models import Case, When, Value, IntegerField
        
        # 1. Lấy danh sách ID những người mà user đang đăng nhập ĐÃ follow
        following_ids = Follows.objects.filter(follower=user).values_list('following_id', flat=True)
        
        # 2. Loại trừ bản thân và những người đã follow, chỉ lấy tài khoản đang hoạt động
        users = Users.objects.exclude(id=user.id).exclude(id__in=following_ids).filter(status='Active')
        
        # 3. Chấm điểm tương đồng (Khoa +2đ, Khóa +1đ, Lớp +1đ)
        score = Value(0, output_field=IntegerField())
        if user.faculty:
            score += Case(When(faculty=user.faculty, then=Value(1)), default=Value(0), output_field=IntegerField())
        if user.academic_year:
            score += Case(When(academic_year=user.academic_year, then=Value(1)), default=Value(0), output_field=IntegerField())
        if user.class_name:
            score += Case(When(class_name=user.class_name, then=Value(1)), default=Value(0), output_field=IntegerField())
            
        # 4. Sắp xếp theo điểm giảm dần, lấy top 5
        users = users.annotate(match_score=score).order_by('-match_score', '-id')[:5]
        
        serializer = UserProfileSerializer(users, many=True, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)