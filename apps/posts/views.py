from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.posts.models import Posts, Categories
from apps.authentication.models import Users
from django.db.models import Case, When, Value, IntegerField

# 1. Serializer con đóng gói thông tin User người đăng
class UserNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['id', 'full_name', 'email', 'role']

# 2. Serializer con đóng gói thông tin Danh mục bài viết
class CategoryNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ['id', 'category_name', 'description']

# 3. Serializer cha đóng gói thông tin Bài viết toàn diện
class PostAdminResponseSerializer(serializers.ModelSerializer):
    # Đổi tên key từ 'user' thành 'author' để khớp 100% với Frontend môn cũ
    author = UserNestedSerializer(source='user', read_only=True)
    category = CategoryNestedSerializer(read_only=True)
    author_name = serializers.CharField(source='user.full_name', read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)

    class Meta:
        model = Posts
        fields = '__all__'

# 4. View xử lý lấy danh sách bài viết (Tên Class chuẩn chỉnh từng chữ để urls.py import)
class PostAdminListAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền truy cập!"}, status=status.HTTP_403_FORBIDDEN)

        # Đẩy bài đang Pending lên đầu, sau đó mới đến các bài khác
        posts = Posts.objects.all().order_by(
            Case(
                # Nếu trạng thái là pending (chấp cả chữ hoa chữ thường), gán mức ưu tiên là 0 (đầu bảng)
                When(status__iexact='pending', then=Value(0)),
                # Các trạng thái còn lại (Accepted, Rejected...) gán mức ưu tiên là 1
                default=Value(1),
                output_field=IntegerField(),
            ),
            '-id' # Sắp xếp phụ: Trong cùng một nhóm trạng thái, bài nào ID lớn hơn (mới hơn) nằm trên
        )

        serializer = PostAdminResponseSerializer(posts, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    
# 5. API XỬ LÝ DUYỆT/TỪ CHỐI BÀI VIẾT
class PostValidateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # 1. PHÂN QUYỀN: Chỉ Admin/Super Admin mới được vào phòng kiểm duyệt
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)
        
        # 2. TÌM BÀI VIẾT: Check xem bài viết cần duyệt có tồn tại không
        try:
            post = Posts.objects.get(pk=pk)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
        
        # 3. BẮT DỮ LIỆU TỪ FRONTEND: Lấy trạng thái và lý do từ body gửi lên
        status_moi = request.data.get('status')
        reject_reason = request.data.get('reject_reason')

        if not status_moi:
            return Response({"detail": "Thiếu trạng thái kiểm duyệt (status)!"}, status=status.HTTP_400_BAD_REQUEST)

        # 4. XỬ LÝ ĐỔI TRẠNG THÁI PHÙ HỢP: Chấp nhận cả chữ hoa chữ thường từ FE gửi lên
        if status_moi.lower() in ['accepted', 'approved']:
            post.status = 'Accepted'
            post.reject_reason = None # Duyệt thành công thì xóa lý do từ chối cũ
            
        elif status_moi.lower() in ['rejected', 'disapproved']:
            post.status = 'Rejected'
            # Nếu FE không truyền lý do, lấy lý do mặc định chuẩn chỉ
            post.reject_reason = reject_reason if reject_reason else 'Bài viết vi phạm tiêu chuẩn cộng đồng.'
            
        else:
            # Phòng hờ trường hợp Frontend gửi trạng thái khác (như Pending...)
            post.status = status_moi

        # Lưu cập nhật xuống SQL Server
        post.save()
        
        serializer = PostAdminResponseSerializer(post)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)