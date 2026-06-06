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
        
        if user_id:
            posts = Posts.objects.filter(
                status__iexact='accepted',
                user_id=user_id
            ).order_by('-id')
        elif scope == 'following':
            from apps.posts.models import Follows
            following_ids = Follows.objects.filter(follower=request.user).values_list('following_id', flat=True)
            posts = Posts.objects.filter(
                status__iexact='accepted',
                user_id__in=following_ids
            ).order_by('-id')
        else:
            # Lấy tất cả các bài viết công khai đã được Admin duyệt
            posts = Posts.objects.filter(status__iexact='accepted').order_by('-id')

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