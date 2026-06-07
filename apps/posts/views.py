"""
APIView và Serializer quản lý phân hệ Bài viết (Posts), Bình luận (Comments),
Tương tác (Likes), Chia sẻ (Share) và Thống kê hệ thống (Dashboard Statistics).

Các phân hệ chính:
- Phân quyền Quản trị (Admin Console): Phê duyệt, từ chối bài viết, xem thống kê.
- Phân quyền Người dùng (User Feed): Tương tác bảng tin sinh viên.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.posts.models import Posts, Categories, Reports, Comments
from apps.authentication.models import Users
from django.db.models import Case, When, Value, IntegerField, Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone

# =====================================================================
# I. ĐỊNH NGHĨA CÁC ĐỐI TƯỢNG ĐÓNG GÓI DỮ LIỆU LỒNG NHAU (NESTED SERIALIZERS)
# =====================================================================

class UserNestedSerializer(serializers.ModelSerializer):
    """Đóng gói thông tin cơ bản của người dùng để tối ưu dung lượng response."""
    class Meta:
        model = Users
        fields = ['id', 'full_name', 'email', 'role']

class CategoryNestedSerializer(serializers.ModelSerializer):
    """Đóng gói thông tin danh mục bài viết phục vụ hiển thị nhãn (Label)."""
    class Meta:
        model = Categories
        fields = ['id', 'category_name', 'description']

class PostAdminResponseSerializer(serializers.ModelSerializer):
    """
    Serializer chuyên biệt phục vụ giao diện quản trị (Admin Panel).
    Bao gồm các thông tin nhạy cảm về kiểm duyệt như trạng thái và lý do từ chối.
    """
    author = UserNestedSerializer(source='user', read_only=True)
    category = CategoryNestedSerializer(read_only=True)
    author_name = serializers.CharField(source='user.full_name', read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)

    class Meta:
        model = Posts
        fields = '__all__'


# =====================================================================
# II. LOGIC NGHIỆP VỤ KIỂM DUYỆT NỘI DUNG (ADMIN MODERATION FLOW)
# =====================================================================

class PostAdminListAPIView(APIView):
    """
    API lấy danh sách bài viết phục vụ hội đồng kiểm duyệt của Admin.
    Sử dụng biểu thức điều kiện Conditional Expression để ưu tiên bài viết 'Pending'.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền truy cập!"}, status=status.HTTP_403_FORBIDDEN)

        # Sắp xếp ưu tiên bài viết đang chờ duyệt (Pending) lên đầu danh sách
        posts = Posts.objects.all().order_by(
            Case(
                When(status__iexact='pending', then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            '-id'
        )

        serializer = PostAdminResponseSerializer(posts, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    

class PostValidateAPIView(APIView):
    """
    API thực thi quyết định phê duyệt bài viết của Quản trị viên.
    Cập nhật trạng thái bài viết và ghi nhận lý do nếu bài viết bị từ chối.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền!"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            post = Posts.objects.get(pk=pk)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
        
        status_moi = request.data.get('status')
        reject_reason = request.data.get('reject_reason')

        if not status_moi:
            return Response({"detail": "Thiếu trạng thái kiểm duyệt (status)!"}, status=status.HTTP_400_BAD_REQUEST)

        # Chuẩn hóa trạng thái đầu vào từ Frontend
        if status_moi.lower() in ['accepted', 'approved']:
            post.status = 'Accepted'
            post.reject_reason = None
            
        elif status_moi.lower() in ['rejected', 'disapproved']:
            post.status = 'Rejected'
            # Ghi nhận lý do nhập tay trực tiếp từ Admin
            post.reject_reason = reject_reason if reject_reason else 'Bài viết vi phạm tiêu chuẩn cộng đồng.'
            
        else:
            post.status = status_moi

        post.save()
        
        serializer = PostAdminResponseSerializer(post)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)


# =====================================================================
# III. LOGIC NGHIỆP VỤ BẢNG TIN SINH VIÊN (USER FEED FLOW)
# =====================================================================

class PostFeedSerializer(serializers.ModelSerializer):
    """
    Serializer bóc tách dữ liệu bài viết hiển thị trên Bảng tin công khai.
    Tự động tính toán số liệu tương tác (Likes, Comments, Attachments) từ các quan hệ liên kết.
    """
    # 🌟 SỬA LỖI CHÍ MẠNG: Đã bổ sung khai báo author đồng bộ với Meta fields
    author = UserNestedSerializer(source='user', read_only=True)
    category = CategoryNestedSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    parent_post = serializers.SerializerMethodField()

    class Meta:
        model = Posts
        fields = [
            'id', 'author', 'category', 'content', 'visibility', 'status', 
            'is_edited', 'created_at', 'updated_at', 'attachments', 'likes', 
            'comments', 'parent_post'
        ]

    def get_attachments(self, obj):
        """Truy vấn danh sách tệp tin đính kèm liên kết qua bảng trung gian."""
        from apps.posts.models import PostAttachments, Attachments
        attachment_ids = PostAttachments.objects.filter(post=obj).values_list('attachment_id', flat=True)
        attachments = Attachments.objects.filter(id__in=attachment_ids)
        return [
            {
                "id": att.id,
                "file_url": att.file_url,
                "view_url": att.file_url,
                "file_type": att.file_type,
                "file_name": att.file_url.split('/')[-1] if att.file_url else ""
            }
            for att in attachments
        ]

    def get_likes(self, obj):
        """Lấy danh sách định danh người dùng đã tương tác thích bài viết."""
        from apps.posts.models import Likes
        likes = Likes.objects.filter(post=obj)
        return [{"user_id": like.user_id} for like in likes]

    def get_comments(self, obj):
        """Tính toán tổng số lượng bình luận tầng phản hồi."""
        return Comments.objects.filter(post=obj).count()

    def get_parent_post(self, obj):
        """Đệ quy cấu trúc bài viết gốc trong trường hợp thực hiện chia sẻ (Share/Repost)."""
        if obj.parent_post:
            return PostFeedSerializer(obj.parent_post).data
        return None


class PostListCreateAPIView(APIView):
    """
    Xử lý truy vấn danh sách Bảng tin có bộ lọc nâng cao (Scope, User, Keyword)
    và khởi tạo bài viết mới từ phía sinh viên.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get('scope', 'all')
        user_id = request.query_params.get('user_id')
        keyword = request.query_params.get('keyword')
        
        # Tiêu chuẩn hiển thị bảng tin: Chỉ hiển thị bài viết đã qua kiểm duyệt thành công
        posts = Posts.objects.filter(status__iexact='accepted')

        # Áp dụng các bộ lọc điều kiện nâng cao nếu có tham số từ client
        if user_id:
            posts = posts.filter(user_id=user_id)
        elif scope == 'following':
            from apps.posts.models import Follows
            following_ids = Follows.objects.filter(follower=request.user).values_list('following_id', flat=True)
            posts = posts.filter(user_id__in=following_ids)
            
        if keyword:
            from django.db.models import Q
            posts = posts.filter(
                Q(content__icontains=keyword) |
                Q(user__full_name__icontains=keyword) |
                Q(category__category_name__icontains=keyword)
            )

        posts = posts.order_by('-id')
        serializer = PostFeedSerializer(posts, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        category_id = request.data.get('category_id')
        content = request.data.get('content')
        visibility = request.data.get('visibility', 'Public')
        
        if not category_id:
            return Response({"detail": "Category là bắt buộc!"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            category = Categories.objects.get(pk=category_id)
        except Categories.DoesNotExist:
            return Response({"detail": "Category không tồn tại!"}, status=status.HTTP_400_BAD_REQUEST)

        # Khởi tạo thực thể bài viết với trạng thái mặc định chờ duyệt (Pending)
        post = Posts.objects.create(
            user=request.user,
            category=category,
            content=content,
            visibility=visibility,
            status='Pending',
            is_edited=False
        )
        
        # Đồng bộ hóa siêu dữ liệu tệp tin đính kèm (đã upload thông qua Object Storage MinIO)
        attachments_data = request.data.get('attachments', [])
        from apps.posts.models import Attachments, PostAttachments
        if attachments_data:
            for att_data in attachments_data:
                att = Attachments.objects.create(
                    file_url=att_data.get('file_url'),
                    file_type=att_data.get('file_type')
                )
                PostAttachments.objects.create(post=post, attachment=att)

        return Response({
            "status": True,
            "data": PostFeedSerializer(post).data
        }, status=status.HTTP_201_CREATED)


class PostDetailAPIView(APIView):
    """Quản lý vòng đời chi tiết bài viết bao gồm: Xem chi tiết, Cập nhật nội dung và Hủy bỏ."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            post = Posts.objects.get(pk=pk)
            if post.user != user:
                return None, Response(
                    {"detail": "Bạn không có quyền chỉnh sửa hoặc xóa bài viết này!"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            return post, None
        except Posts.DoesNotExist:
            return None, Response(
                {"detail": "Không tìm thấy bài viết!"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, pk):
        try:
            post = Posts.objects.get(pk=pk)
            if post.status != 'Accepted' and post.user != request.user:
                return Response({"detail": "Bài viết chưa được duyệt hoặc bạn không có quyền xem!"}, status=status.HTTP_403_FORBIDDEN)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = PostFeedSerializer(post)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, pk):
        post, error_response = self.get_object(pk, request.user)
        if error_response: return error_response

        category_id = request.data.get('category_id')
        if category_id:
            try:
                category = Categories.objects.get(pk=category_id)
                post.category = category
            except Categories.DoesNotExist:
                pass
        
        content = request.data.get('content')
        if content is not None:
            post.content = content
            post.is_edited = True
            
        visibility = request.data.get('visibility')
        if visibility:
            post.visibility = visibility

        post.save()

        # Làm mới mảng tệp tin đính kèm nếu phía client có sự thay đổi cấu trúc tệp
        attachments_data = request.data.get('attachments')
        if attachments_data is not None:
            from apps.posts.models import Attachments, PostAttachments
            PostAttachments.objects.filter(post=post).delete()
            for att_data in attachments_data:
                att = Attachments.objects.create(
                    file_url=att_data.get('file_url'),
                    file_type=att_data.get('file_type')
                )
                PostAttachments.objects.create(post=post, attachment=att)

        return Response({
            "status": True,
            "data": PostFeedSerializer(post).data
        }, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        post, error_response = self.get_object(pk, request.user)
        if error_response: return error_response

        post.delete()
        return Response({
            "status": True,
            "data": {"detail": "Xóa bài viết thành công"}
        }, status=status.HTTP_200_OK)


class PostLikeAPIView(APIView):
    """Xử lý hành vi tương tác Thích/Bỏ thích bài viết sử dụng cơ chế Hoán đổi (Toggle Logic)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Posts.objects.get(pk=pk)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
            
        from apps.posts.models import Likes
        like, created = Likes.objects.get_or_create(post=post, user=request.user)
        
        if not created:
            like.delete()
            return Response({"data": {"detail": "Đã bỏ thích", "liked": False}}, status=status.HTTP_200_OK)
            
        return Response({"data": {"detail": "Đã thích", "liked": True}}, status=status.HTTP_200_OK)


class PostShareAPIView(APIView):
    """Xử lý hành vi Repost/Share thông qua việc thiết lập khóa ngoại liên kết tuyến tính (parent_post)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            parent_post = Posts.objects.get(pk=pk)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
            
        content = request.data.get('content', '')
        
        new_post = Posts.objects.create(
            user=request.user,
            category=parent_post.category,
            parent_post=parent_post,
            content=content,
            visibility='Public',
            status='Accepted', # Đối với bài viết chia sẻ từ nguồn hợp lệ thì không cần duyệt lại nguồn
            is_edited=False
        )
        
        return Response({
            "data": PostFeedSerializer(new_post).data
        }, status=status.HTTP_201_CREATED)


# =====================================================================
# IV. PHÂN HỆ QUẢN LÝ TƯƠNG TÁC BÌNH LUẬN (COMMENTS LOGIC)
# =====================================================================

class CommentSerializer(serializers.ModelSerializer):
    """Serializer hỗ trợ đóng gói phân hệ bình luận dạng cây phân cấp (Threaded Reply)."""
    user = UserNestedSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    parent_comment_id = serializers.ReadOnlyField()
    post_id = serializers.ReadOnlyField()

    class Meta:
        model = Comments
        fields = ['id', 'post_id', 'user', 'parent_comment_id', 'content', 'created_at', 'updated_at', 'attachments']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_attachments(self, obj):
        try:
            from apps.posts.models import CommentAttachments, Attachments
            attachment_ids = CommentAttachments.objects.filter(comment=obj).values_list('attachment_id', flat=True)
            attachments = Attachments.objects.filter(id__in=attachment_ids)
            return [
                {
                    "id": att.id,
                    "file_url": att.file_url,
                    "view_url": att.file_url,
                    "file_type": att.file_type,
                    "file_name": att.file_url.split('/')[-1] if att.file_url else ""
                }
                for att in attachments
            ]
        except Exception:
            return []


class CommentListCreateAPIView(APIView):
    """Truy vấn danh sách bình luận theo ngữ cảnh bài viết và tạo bình luận mới (hỗ trợ Reply lồng nhau)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = Posts.objects.get(pk=post_id)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
            
        comments = Comments.objects.filter(post=post).order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, post_id):
        try:
            post = Posts.objects.get(pk=post_id)
        except Posts.DoesNotExist:
            return Response({"detail": "Không tìm thấy bài viết!"}, status=status.HTTP_404_NOT_FOUND)
            
        content = request.data.get('content')
        parent_comment_id = request.data.get('parent_comment_id')
        attachments_data = request.data.get('attachments', [])
        
        if not content and not attachments_data:
            return Response({"detail": "Nội dung hoặc file đính kèm là bắt buộc!"}, status=status.HTTP_400_BAD_REQUEST)
            
        parent_comment = None
        if parent_comment_id:
            try:
                parent_comment = Comments.objects.get(pk=parent_comment_id, post=post)
            except Comments.DoesNotExist:
                return Response({"detail": "Bình luận cha không tồn tại!"}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comments.objects.create(
            post=post,
            user=request.user,
            parent_comment=parent_comment,
            content=content
        )
        
        if attachments_data:
            try:
                from apps.posts.models import Attachments, CommentAttachments
                for att_data in attachments_data:
                    att = Attachments.objects.create(
                        file_url=att_data.get('file_url'),
                        file_type=att_data.get('file_type')
                    )
                    CommentAttachments.objects.create(comment=comment, attachment=att)
            except ImportError:
                pass

        return Response({
            "status": True,
            "data": CommentSerializer(comment).data
        }, status=status.HTTP_201_CREATED)


class CommentDetailAPIView(APIView):
    """Cập nhật nội dung hoặc gỡ bỏ hoàn toàn phản hồi bình luận khỏi hệ thống cơ sở dữ liệu."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            comment = Comments.objects.get(pk=pk)
            if comment.user != user and user.role not in ['Admin', 'Super Admin']:
                return None, Response({"detail": "Bạn không có quyền thao tác với bình luận này!"}, status=status.HTTP_403_FORBIDDEN)
            return comment, None
        except Comments.DoesNotExist:
            return None, Response({"detail": "Không tìm thấy bình luận!"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        comment, error_response = self.get_object(pk, request.user)
        if error_response: return error_response

        if comment.user != request.user:
            return Response({"detail": "Chỉ tác giả mới được sửa bình luận!"}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content')
        if content is not None:
            comment.content = content
            comment.save()

        return Response({
            "status": True,
            "data": CommentSerializer(comment).data
        }, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        comment, error_response = self.get_object(pk, request.user)
        if error_response: return error_response

        comment.delete()
        return Response({
            "status": True,
            "data": {"detail": "Xóa bình luận thành công"}
        }, status=status.HTTP_200_OK)


# =====================================================================
# VI. PHÂN HỆ PHÂN TÍCH VÀ THỐNG KÊ SỐ LIỆU ĐỒNG BỘ (STATS & TRENDING APIs)
# =====================================================================

class CategoryTrendingAPIView(APIView):
    """API thống kê Top 5 danh mục có mật độ tương tác và số lượng bài đăng cao nhất (Trending Topics)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trending = Posts.objects.filter(status__iexact='accepted') \
            .values('category__id', 'category__category_name', 'category__description') \
            .annotate(post_count=Count('id')) \
            .order_by('-post_count')[:5]
        
        data = [
            {
                "id": item['category__id'],
                "category_name": item['category__category_name'],
                "description": item['category__description'],
                "post_count": item['post_count']
            } for item in trending
        ]
        
        return Response({"data": data}, status=status.HTTP_200_OK)


class DashboardStatsAPIView(APIView):
    """
    API tổng hợp số liệu Dashboard quản trị toàn diện.
    Thực hiện tổng hợp số liệu (Aggregation) thời gian thực và đồng bộ cấu trúc 
    đầu ra đa chuẩn định dạng (camelCase và snake_case) để tương thích tối đa với Client Side Components.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền xem dữ liệu thống kê này!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            # 1. Truy vấn các chỉ số đo lường cốt lõi (Core Metrics) từ SQL Server
            total_users = Users.objects.count()
            total_posts = Posts.objects.count()
            pending_posts = Posts.objects.filter(status__iexact='pending').count()
            total_reports = Reports.objects.count()

            # Phân bổ bài viết theo các trạng thái kiểm duyệt hiện tại
            post_status_counts = Posts.objects.values('status').annotate(total=Count('id'))
            status_distribution = {item['status']: item['total'] for item in post_status_counts}

            # Phân bổ số lượng bài viết tương ứng với từng danh mục hệ thống
            category_counts = Posts.objects.values('category__category_name').annotate(total=Count('id'))
            
            # Đóng gói cấu trúc mảng tương thích với sơ đồ giao diện Frontend React Card/Offbar
            post_by_category_data = [
                {
                    "category_name": item['category__category_name'] if item['category__category_name'] else "Chưa phân loại",
                    "total": str(item['total']) # Định dạng kiểu chuỗi ký tự theo giao diện TypeScript quy định
                } for item in category_counts
            ]

            # Biểu đồ xu hướng phát triển bài viết mới trong chu kỳ 7 ngày gần nhất
            seven_days_ago = timezone.now() - timedelta(days=7)
            daily_posts = Posts.objects.filter(created_at__gte=seven_days_ago)\
                .annotate(date=TruncDate('created_at'))\
                .values('date')\
                .annotate(total=Count('id'))\
                .order_by('date')

            post_trend = [
                {
                    "date": item['date'].strftime('%d/%m') if item['date'] else "",
                    "total": item['total']
                } for item in daily_posts
            ]

            # 2. Xây dựng cấu trúc phản hồi an toàn (Fallback & Rải thảm dữ liệu cấu trúc lồng)
            dashboard_data = {
                "users": total_users,
                "posts": total_posts,
                "reports": total_reports,
                "postByCategory": post_by_category_data,

                # Thuộc tính mở rộng tương thích với chuẩn camelCase của các Admin UI template cũ
                "totalUsers": total_users,
                "totalPosts": total_posts,
                "openReports": total_reports,
                "totalReports": total_reports,
                "pendingPosts": pending_posts,
                
                "total_users": total_users,
                "total_posts": total_posts,
                "open_reports": total_reports,
                "pending_posts": pending_posts,

                "summary": {
                    "totalUsers": total_users,
                    "totalPosts": total_posts,
                    "openReports": total_reports,
                    "total_users": total_users,
                    "total_posts": total_posts,
                    "open_reports": total_reports,
                },
                
                "statusChart": status_distribution,
                "status_chart": status_distribution,
                "status": status_distribution,
                
                "categoryChart": post_by_category_data,
                "category_chart": post_by_category_data,
                "categories": post_by_category_data,
                
                "postTrendChart": post_trend,
                "post_trend_chart": post_trend,
                "trend": post_trend
            }

            # Xử lý bao sân tầng bọc Axios Client của Frontend
            dashboard_data["data"] = dashboard_data.copy()

            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Lỗi tính toán dữ liệu Dashboard thống kê: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )