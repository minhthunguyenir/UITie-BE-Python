"""
Views cho module Authentication.

File này chứa các endpoint xử lý login, quản lý tài khoản (CRUD),
khóa/mở khóa, profile, follow, tìm kiếm và gợi ý follow.

"""

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
    """
    Xử lý đăng nhập và phát token JWT.

    Tại sao:
    - Tách riêng endpoint đăng nhập để dễ áp dụng các policy bảo mật
      (rate-limit, MFA, logging) mà không ảnh hưởng tới các API khác.
    - Trả về cấu trúc đáp ứng khớp Frontend để giảm thay đổi client.
    """

    def post(self, request):
        """
        Thực hiện các bước xác thực:
        1) Validate payload từ Frontend
        2) Tìm user theo email
        3) Kiểm tra trạng thái tài khoản (Locked/Inactive)
        4) So khớp mật khẩu (hash)
        5) Trả về access token và thông tin user
        """
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response({"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, status=status.HTTP_401_UNAUTHORIZED)

        # Nếu tài khoản bị khóa/không kích hoạt thì chặn sớm, tránh lộ thông tin
        if user.status == 'Locked':
            return Response({"detail": f"Tài khoản đã bị khóa! Lý do: {user.status_reason or 'Không có'}"}, status=status.HTTP_403_FORBIDDEN)
        elif user.status == 'Inactive':
            return Response({"detail": "Tài khoản chưa được kích hoạt!"}, status=status.HTTP_403_FORBIDDEN)

        if not check_password(password, user.password):
            return Response({"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        return Response({"data": {"user": UserResponseSerializer(user).data, "token": str(refresh.access_token)}}, status=status.HTTP_200_OK)

class UserListAPIView(APIView):
    """
    Quản lý danh sách người dùng và tạo tài khoản (Admin area).

    Tại sao:
    - Giới hạn chỉ Admin/Super Admin gọi được để đảm bảo phân quyền.
    - Khi tạo user cần thêm kiểm tra nâng cao để tránh Admin thường
      vô tình hoặc cố ý tạo tài khoản có quyền cao hơn.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Trả về danh sách user để hiển thị trong admin panel.

        Lưu ý: truy vấn trả về tất cả users và frontend chịu trách nhiệm
        phân trang/hiển thị; backend giữ logic phân quyền.
        """
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền truy cập tính năng này!"}, status=status.HTTP_403_FORBIDDEN)

        users = Users.objects.all().order_by('-id')
        serializer = UserResponseSerializer(users, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Tạo tài khoản mới (dành cho Admin/Super-Admin).

        Business rules:
        - Student không được phép tạo tài khoản.
        - Admin thường không được tạo tài khoản Admin/Super Admin.
        """
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền thực hiện hành động này!"}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role == 'Admin':
            role_muon_tao = request.data.get('role')
            if role_muon_tao in ['Super Admin', 'Admin']:
                return Response({"detail": "Tài khoản Admin thường chỉ được phép tạo tài khoản cho Student"}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSaveSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"data": UserResponseSerializer(user).data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserDetailAPIView(APIView):
    """
    Xem và sửa thông tin từng người dùng (Admin area).

    Tại sao: tách endpoint chi tiết theo ID để áp dụng audit và
    business validations riêng trước khi cập nhật (ví dụ không cho
    Admin thường sửa Admin khác).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """
        Cập nhật partial thông tin user theo ID.

        Kiểm tra phân quyền nâng cao theo SRS:
        - Chỉ Admin/Super Admin được phép vào endpoint này.
        - Admin thường không được sửa tài khoản cấp cao hoặc nâng quyền.
        """
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_to_update = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'Admin':
            if user_to_update.role in ['Super Admin', 'Admin']:
                return Response({"detail": "Tài khoản Admin thường không có quyền chỉnh sửa tài khoản cấp cao khác!"}, status=status.HTTP_403_FORBIDDEN)
            role_moi = request.data.get('role')
            if role_moi in ['Super Admin', 'Admin']:
                return Response({"detail": "Admin thường không thể nâng cấp tài khoản lên quyền Admin/Super Admin!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserSaveSerializer(user_to_update, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({"data": UserResponseSerializer(updated_user).data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    """
    Xem và cập nhật hồ sơ cá nhân.

    Tại sao: quyền chỉnh sửa profile chỉ thuộc về chính owner; việc
    tách riêng GET/PUT giúp backend kiểm soát an toàn (không cho user
    sửa email/role/status qua endpoint này).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """Trả về profile của chính user hoặc profile theo ID nếu được truyền."""
        try:
            user = Users.objects.get(pk=pk) if pk else request.user
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng!"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        """
        Owner-only update: chặn việc user cố tình truyền id người khác.
        Cho phép cập nhật một số trường cá nhân được whitelist ở serializer.
        """
        if pk and str(pk) != str(request.user.id):
            return Response({"detail": "Bạn không có quyền chỉnh sửa hồ sơ của người khác!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({"data": UserProfileSerializer(updated_user, context={'request': request}).data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserFollowAPIView(APIView):
    """
    Follow/unfollow người dùng.

    Tại sao: hành động follow là toggle (idempotent tại mức business):
    - Nếu đã follow thì un-follow, ngược lại tạo quan hệ follow mới.
    - Không cho phép follow chính mình.
    """

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
    """
    Khóa tài khoản (chuyển status -> 'Locked').

    Tại sao: thao tác khóa nên tách biệt với cập nhật thông tin chung để
    đảm bảo chỉ thay đổi trạng thái, đồng thời cho phép ghi lý do khóa
    (status_reason) khi cần cho mục audit.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_to_lock = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'Admin' and user_to_lock.role in ['Super Admin', 'Admin']:
            return Response({"detail": "Tài khoản Admin thường không có quyền khóa tài khoản cấp cao khác!"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['status'] = 'Locked'

        serializer = UserSaveSerializer(user_to_lock, data=data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({"data": UserResponseSerializer(updated_user).data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserUnlockAPIView(APIView):
    """
    Mở khóa tài khoản (chuyển status -> 'Active').

    Tại sao: cần endpoint riêng để phân biệt intent (unlock vs general update)
    và áp các kiểm soát phân quyền tương tự như khi khóa.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_to_unlock = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'Admin' and user_to_unlock.role in ['Super Admin', 'Admin']:
            return Response({"detail": "Tài khoản Admin thường không có quyền mở khóa tài khoản cấp cao khác!"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['status'] = 'Active'

        serializer = UserSaveSerializer(user_to_unlock, data=data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({"data": UserResponseSerializer(updated_user).data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchAPIView(APIView):
    """
    Tìm kiếm người dùng theo keyword.

    Tại sao: tách riêng search endpoint để có thể tối ưu hóa (index,
    ranking, paginate) mà không ảnh hưởng tới API list/CRUD.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        if keyword:
            from django.db.models import Q
            users = Users.objects.filter(
                Q(full_name__icontains=keyword) | Q(email__icontains=keyword) | Q(mssv__icontains=keyword)
            ).order_by('-id')
        else:
            users = Users.objects.none()

        serializer = UserResponseSerializer(users, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

class UserSuggestedFollowsAPIView(APIView):
    """
    Gợi ý người dùng nên follow (recommendation đơn giản trên DB).

    Tại sao: cung cấp fallback recommendation dựa trên các tiêu chí
    có sẵn (faculty, academic_year, class) để gợi ý nhanh cho UI sidebar.
    Thiết kế này dễ chạy trực tiếp trên DB (annotate) và phù hợp với
    dataset nhỏ/ trung bình. Nếu scale, nên thay bằng hệ thống đề xuất riêng.
    """

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