"""
APIView xử lý phân hệ Xác thực (Authentication), Phân quyền (Authorization)
và Quản trị tài khoản người dùng (User Management Profile).

Các chức năng chính tích hợp trong module:
- Cấp phát Token định danh bảo mật tập trung qua chuẩn mã hóa JSON Web Token (JWT).
- Phân định luồng kiểm soát truy cập dựa trên vai trò người dùng (Role-based Access Control - RBAC).
- Quản trị thông tin hồ sơ cá nhân, tìm kiếm nâng cao và thuật toán gợi ý kết nối.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from apps.authentication.models import Users
from apps.authentication.serializers import (
    LoginRequestSerializer, UserResponseSerializer, 
    UserSaveSerializer, UserProfileSerializer, ProfileUpdateSerializer
)
from django.utils import timezone

# =====================================================================
# I. PHÂN HỆ XÁC THỰC VÀ ĐĂNG NHẬP HỆ THỐNG (AUTHENTICATION FLOW)
# =====================================================================

class LoginAPIView(APIView):
    """
    Điểm cuối xử lý đăng nhập, kiểm tra tính toàn vẹn và cấp phát token JWT.
    
    Thiết kế tách biệt phân hệ đăng nhập độc lập giúp dễ dàng tích hợp các chính sách
    bảo mật nâng cao (như Rate-limiting, ghi log kiểm toán Audit log) mà không ảnh hưởng
    tới hiệu năng vận hành tổng thể của các API nghiệp vụ khác.
    """

    def post(self, request):
        """
        Thực hiện quy trình xác thực đa tầng kiểm định đầu vào:
        1) Kiểm tra tính hợp lệ của cấu trúc dữ liệu gửi lên (Payload Validation).
        2) Kiểm tra ràng buộc định dạng tên miền email nội bộ của cơ sở giáo dục.
        3) Truy vấn thực thể người dùng, xác định trạng thái kích hoạt/khóa mềm của tài khoản.
        4) Xác thực chữ ký mã hóa mật khẩu thông qua thuật toán băm (Bcrypt/PBKDF2).
        5) Khởi tạo và phản hồi cặp mã token truy cập an toàn (Access Token).
        """
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # -----------------------------------------------------------------
        # [RÀNG BUỘC NGHIỆP VỤ TC_AUTH_04]: Kiểm tra định dạng tên miền email nội bộ
        # Chặn xử lý sớm ngay tại tầng ứng dụng nếu người dùng sử dụng email cá nhân ngoài hệ thống
        # -----------------------------------------------------------------
        if not email.endswith('@ms.uit.edu.vn'):
            return Response(
                {"detail": "Vui lòng sử dụng email @ms.uit.edu.vn."}, 
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response(
                {"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # -----------------------------------------------------------------
        # [RÀNG BUỘC NGHIỆP VỤ TC_AUTH_05]: Kiểm tra trạng thái hoạt động của tài khoản
        # Chặn các yêu cầu đăng nhập từ tài khoản đang trong diện bị đình chỉ (Blocked/Locked)
        # -----------------------------------------------------------------
        if user.status in ['Blocked', 'Locked']:
            return Response(
                {"detail": "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ Admin."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        elif user.status == 'Inactive':
            return Response(
                {"detail": "Tài khoản chưa được kích hoạt!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Kiểm tra tính đúng đắn của mật khẩu thông qua hàm so khớp chuỗi băm an toàn
        if not check_password(password, user.password):
            return Response(
                {"detail": "Tài khoản hoặc mật khẩu không chính xác!"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Khởi tạo chu kỳ mã Token định danh JWT mới cho phiên làm việc hợp lệ
        refresh = RefreshToken.for_user(user)

        return Response({
            "data": {
                "user": UserResponseSerializer(user).data, 
                "token": str(refresh.access_token)
            }
        }, status=status.HTTP_200_OK)


# =====================================================================
# II. PHÂN HỆ QUẢN TRỊ TÀI KHOẢN TẬP TRUNG CHỦ QUẢN (ADMIN AREA - RBAC)
# =====================================================================

class UserListAPIView(APIView):
    """
    Điểm cuối hỗ trợ truy xuất danh sách tổng quan và khởi tạo tài khoản mới.
    Áp dụng cơ chế phân quyền kiểm soát nghiêm ngặt theo mô hình RBAC.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Truy xuất danh sách toàn bộ người dùng phục vụ bảng quản trị của Admin/Super Admin."""
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền truy cập tính năng này!"}, status=status.HTTP_403_FORBIDDEN)

        users = Users.objects.all().order_by('-id')
        serializer = UserResponseSerializer(users, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Khởi tạo tài khoản sinh viên mới từ hội đồng quản trị hệ thống.
        Chứa logic bẫy phân cấp quyền hạn: Ngăn chặn tài khoản Admin cấp thấp tự ý khởi tạo
        hoặc nâng quyền cho các tài khoản Admin đồng cấp hoặc Super Admin cấp cao hơn.
        """
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền thực hiện hành động này!"}, status=status.HTTP_403_FORBIDDEN)

        # Ràng buộc kiểm soát phân cấp: Chỉ cho phép Admin thường khởi tạo tài khoản phân quyền Student
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
    """Xử lý cập nhật thông tin chi tiết từng thực thể người dùng cụ thể thông qua định danh khóa chính (ID)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """
        Cập nhật từng phần thuộc tính của người dùng (Partial Update).
        Thực thi các quy tắc kiểm tra ràng buộc phân cấp nghiêm ngặt nhằm tránh leo thang đặc quyền trái phép.
        """
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_to_update = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng này!"}, status=status.HTTP_404_NOT_FOUND)

        # Ngăn chặn việc Admin thông thường can thiệp sửa đổi cấu trúc dữ liệu của các Admin quản trị khác
        if request.user.role == 'Admin':
            if user_to_update.role in ['Super Admin', 'Admin']:
                return Response({"detail": "Tài khoản Admin thường không có quyền chỉnh sửa tài khoản cấp cao khác!"}, status=status.HTTP_403_FORBIDDEN)
            
            role_moi = request.data.get('role')
            if role_moi in ['Super Admin', 'Admin']:
                return Response({"detail": "Admin thường không thể nâng cấp tài khoản lên quyền Admin/Super Admin!"}, status=status.HTTP_403_FORBIDGEN)

        serializer = UserSaveSerializer(user_to_update, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response({"data": UserResponseSerializer(updated_user).data}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# III. PHÂN HỆ XỬ LÝ HỒ SƠ VÀ TƯƠNG TÁC XÃ HỘI (USER PROFILE & INTERACTIONS)
# =====================================================================

class UserProfileAPIView(APIView):
    """Phân hệ cho phép cá nhân người dùng tự truy xuất và cập nhật thông tin hồ sơ (Owner-only operation)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        """Truy xuất thông tin hồ sơ chi tiết. Hỗ trợ hiển thị profile cá nhân hoặc profile công khai của thành viên khác."""
        try:
            user = Users.objects.get(pk=pk) if pk else request.user
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng!"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        """
        Cập nhật thông tin cá nhân. Chặn hoàn toàn hành vi thay đổi thuộc tính hồ sơ của người khác.
        Chỉ cho phép thay đổi các trường dữ liệu được Whitelist (như Tiểu sử, Avatar) để bảo vệ tính toàn vẹn hệ thống.
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
    Xử lý mối quan hệ kết nối giữa các thực thể người dùng hệ thống.
    Áp dụng cơ chế hoán đổi trạng thái Toggle Logic (Idempotent tại mức logic nghiệp vụ).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """
        Thực hiện thiết lập hoặc hủy bỏ mối quan hệ theo dõi (Follow/Unfollow).
        Ràng buộc bắt buộc: Người dùng tuyệt đối không được tự thiết lập mối quan hệ theo dõi chính mình.
        """
        try:
            target_user = Users.objects.get(pk=pk)
        except Users.DoesNotExist:
            return Response({"detail": "Không tìm thấy người dùng!"}, status=status.HTTP_404_NOT_FOUND)

        if target_user == request.user:
            return Response({"detail": "Bạn không thể tự theo dõi chính mình!"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.posts.models import Follows
        follow = Follows.objects.filter(follower=request.user, following=target_user).first()

        if follow:
            # Nếu mối quan hệ đã tồn tại -> Thực hiện cơ chế Hủy theo dõi (Unfollow)
            follow.delete()
            return Response({"data": {"detail": "Đã bỏ theo dõi", "is_following": False}}, status=status.HTTP_200_OK)
        else:
            # Nếu mối quan hệ chưa tồn tại -> Khởi tạo bản ghi liên kết mới vào bảng trung gian
            Follows.objects.create(follower=request.user, following=target_user, created_at=timezone.now(), updated_at=timezone.now())
            return Response({"data": {"detail": "Đã theo dõi", "is_following": True}}, status=status.HTTP_200_OK)
        

# =====================================================================
# IV. PHÂN HỆ KIỂM SOÁT TRẠNG THÁI TÀI KHOẢN AN TOÀN (AUDIT LOCK LOGIC)
# =====================================================================

class UserLockAPIView(APIView):
    """API chuyên biệt phục vụ thao tác đình chỉ và khóa cứng quyền truy cập của tài khoản vi phạm tiêu chuẩn."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """Chuyển đổi trạng thái thực thể người dùng sang trạng thái 'Locked' kèm theo lý do vi phạm phục vụ công tác kiểm toán."""
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
    """API phục hồi quyền hoạt động cho tài khoản người dùng sau thời gian chấp hành kỷ luật."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        """Khôi phục trạng thái hoạt động thực thể về trạng thái 'Active' và gỡ bỏ hoàn toàn các lệnh hạn chế truy cập."""
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


# =====================================================================
# V. BỘ LỌC TÌM KIẾM ĐA TIÊU CHÍ VÀ THUẬT TOÁN GỢI Ý KẾT NỐI (SEARCH & RECOMMENDATION)
# =====================================================================

class UserSearchAPIView(APIView):
    """Phân hệ truy vấn tìm kiếm người dùng. Hỗ trợ tìm kiếm mờ (Fuzzy Search) đa tiêu chí dữ liệu đầu vào."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Thực hiện tìm kiếm song song theo Họ tên (full_name), Email liên kết, hoặc Mã số sinh viên (mssv)."""
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
    """
    Hệ thống khuyến nghị kết nối đồng đẳng (Simple Fallback Recommendation Engine).
    Tính toán trọng số dựa trên mức độ tương đồng về thuộc tính định danh trong môi trường đại học.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Tính toán chấm điểm tương đồng để gợi ý Top 5 người dùng phù hợp nhất:
        - Điều kiện loại trừ: Loại bỏ chính mình, loại bỏ tài khoản đã theo dõi, loại bỏ tài khoản bị khóa.
        - Cơ chế chấm điểm (Scoring Weight): Trùng Khoa (Faculty) +1đ, trùng Khóa học (Academic Year) +1đ, trùng Lớp sinh hoạt (Class Name) +1đ.
        """
        user = request.user
        from apps.posts.models import Follows
        from django.db.models import Case, When, Value, IntegerField

        # Thu thập mảng danh sách ID của các tài khoản đã được thiết lập theo dõi trước đó
        following_ids = Follows.objects.filter(follower=user).values_list('following_id', flat=True)

        # Thiết lập bộ lọc loại trừ cốt lõi bảo vệ luồng thuật toán
        users = Users.objects.exclude(id=user.id).exclude(id__in=following_ids).filter(status='Active')

        # Khởi tạo biểu thức điều kiện tính điểm tương đồng thực thể thời gian thực
        score = Value(0, output_field=IntegerField())
        if user.faculty:
            score += Case(When(faculty=user.faculty, then=Value(1)), default=Value(0), output_field=IntegerField())
        if user.academic_year:
            score += Case(When(academic_year=user.academic_year, then=Value(1)), default=Value(0), output_field=IntegerField())
        if user.class_name:
            score += Case(When(class_name=user.class_name, then=Value(1)), default=Value(0), output_field=IntegerField())

        # Sắp xếp danh sách theo tổng điểm ưu tiên giảm dần và lấy Top 5 bản ghi tốt nhất
        users = users.annotate(match_score=score).order_by('-match_score', '-id')[:5]

        serializer = UserProfileSerializer(users, many=True, context={'request': request})
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)