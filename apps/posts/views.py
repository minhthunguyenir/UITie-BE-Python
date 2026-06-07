from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.posts.models import Posts, Categories, Reports
from apps.authentication.models import Users
from django.db.models import Case, When, Value, IntegerField, Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone

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
            # Admin tự nhập tay lý do từ body truyền lên thay vì chọn sẵn
            post.reject_reason = reject_reason if reject_reason else 'Bài viết vi phạm tiêu chuẩn cộng đồng.'
            
        else:
            # Phòng hờ trường hợp Frontend gửi trạng thái khác (như Pending...)
            post.status = status_moi

        # Lưu cập nhật xuống SQL Server
        post.save()
        
        serializer = PostAdminResponseSerializer(post)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

# 6. Serializer cho luồng Feed (Bảng tin)
class PostFeedSerializer(serializers.ModelSerializer):
    author = UserNestedSerializer(source='user', read_only=True)
    category = CategoryNestedSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    parent_post = serializers.SerializerMethodField()

    class Meta:
        model = Posts
        fields = ['id', 'author', 'category', 'content', 'visibility', 'status', 'is_edited', 'created_at', 'updated_at', 'attachments', 'likes', 'comments', 'parent_post']

    def get_attachments(self, obj):
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
        from apps.posts.models import Likes
        likes = Likes.objects.filter(post=obj)
        return [{"user_id": like.user_id} for like in likes]

    def get_comments(self, obj):
        from apps.posts.models import Comments
        return Comments.objects.filter(post=obj).count()

    def get_parent_post(self, obj):
        if obj.parent_post:
            return PostFeedSerializer(obj.parent_post).data
        return None

# 7. Lấy danh sách Feed và Đăng bài viết
class PostListCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get('scope', 'all')
        user_id = request.query_params.get('user_id')
        keyword = request.query_params.get('keyword')
        
        # Chỉ lấy bài viết đã duyệt
        posts = Posts.objects.filter(status__iexact='accepted')

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

        post = Posts.objects.create(
            user=request.user,
            category=category,
            content=content,
            visibility=visibility,
            status='Pending', # Mặc định bài đăng cần Admin duyệt
            is_edited=False
        )
        
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

# 8. API Sửa, Xóa bài viết
class PostDetailAPIView(APIView):
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
            # Chỉ cho phép xem nếu bài đã được duyệt hoặc người đang xem chính là tác giả
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

# 9. API Like/Bỏ Like
class PostLikeAPIView(APIView):
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

# 10. API Chia sẻ bài viết
class PostShareAPIView(APIView):
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
            status='Accepted',
            is_edited=False
        )
        
        return Response({
            "data": PostFeedSerializer(new_post).data
        }, status=status.HTTP_201_CREATED)

# 11. API Bình luận
from apps.posts.models import Comments

class CommentSerializer(serializers.ModelSerializer):
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

# 12. API Danh mục xu hướng
class CategoryTrendingAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Join qua bảng Posts, đếm số lượng bài viết 'Accepted' cho từng danh mục
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

# 13. API THỐNG KÊ DASHBOARD TOÀN DIỆN CHO ADMIN
class DashboardStatsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['Super Admin', 'Admin']:
            return Response({"detail": "Bạn không có quyền xem dữ liệu thống kê này!"}, status=status.HTTP_403_FORBIDDEN)

        try:
            # 1. Tính toán số liệu từ SQL Server (Giữ nguyên)
            total_users = Users.objects.count()
            total_posts = Posts.objects.count()
            pending_posts = Posts.objects.filter(status__iexact='pending').count()
            total_reports = Reports.objects.count()

            post_status_counts = Posts.objects.values('status').annotate(total=Count('id'))
            status_distribution = {item['status']: item['total'] for item in post_status_counts}

            category_counts = Posts.objects.values('category__category_name').annotate(total=Count('id'))
            
            # 🌟 ĐÓN ĐẦU BIỂU ĐỒ: Tạo mảng postByCategory chuẩn chỉnh cấu hình Frontend
            post_by_category_data = [
                {
                    "category_name": item['category__category_name'] if item['category__category_name'] else "Chưa phân loại",
                    "total": str(item['total']) # Ép về kiểu string chuẩn đét theo file statistic.ts của FE
                } for item in category_counts
            ]

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

            # 🚀 HỆ THỐNG BIẾN BAO SÂN - KHỚP 100% VỚI INTERFACE STATISTICS
            dashboard_data = {
                # 3 biến Core cứu sống 3 cái ô Overview lúc nãy của Thư
                "users": total_users,
                "posts": total_posts,
                "reports": total_reports,
                
                # 🌟 CHIÊU CUỐI: Trả về đúng key 'postByCategory' để kích hoạt biểu đồ cột/tròn
                "postByCategory": post_by_category_data,

                # Bọc lót thêm các biến camelCase và gạch dưới đề phòng các màn hình khác gọi ké
                "totalUsers": total_users,
                "totalPosts": total_posts,
                "openReports": total_reports,
                "total_users": total_users,
                "total_posts": total_posts,
                "open_reports": total_reports,
                "status_chart": status_distribution,
                "post_trend_chart": post_trend,
                "trend": post_trend
            }

            # Nhân bản thêm một tầng "data" bên trong để trị dứt điểm lỗi quên viết .then(res => res.data) của FE
            dashboard_data["data"] = dashboard_data.copy()

            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Lỗi tính toán dữ liệu Dashboard thống kê: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )