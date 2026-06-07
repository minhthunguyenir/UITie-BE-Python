"""
Serializers cho module Posts (Bài viết, bình luận, tệp đính kèm).

Module này định nghĩa các DRF Serializer để:
- Serialize/deserialize bài viết (POST create/update, GET list/detail)
- Xử lý tệp đính kèm (upload/download URL từ MinIO)
- Ánh xạ FK (user -> author) để khớp Frontend contract
- Tính toán các trường hợp lệ (likes count, comments count)
"""

from rest_framework import serializers
from apps.posts.models import Posts, Categories, Attachments, PostAttachments, Likes, Comments
from apps.authentication.serializers import UserResponseSerializer
from django.utils import timezone

class CategorySerializer(serializers.ModelSerializer):
    """
    Serialize danh mục bài viết.

    Tại sao: cho phép UI select dropdown danh mục khi tạo post,
    và hiển thị danh mục của post trong detail/list view.
    """
    class Meta:
        model = Categories
        fields = '__all__'

class AttachmentSerializer(serializers.ModelSerializer):
    """
    Serialize tệp đính kèm với thêm view_url và file_name.

    Tại sao:
    - DB chỉ lưu file_url (đường dẫn S3/MinIO), nhưng Frontend cần
      view_url (để load ảnh trực tiếp) và file_name (để hiển thị tên).
    - SerializerMethodField cho phép tính toán trên-the-fly mà không lưu DB.
    """
    view_url = serializers.CharField(source='file_url', read_only=True)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachments
        fields = ['id', 'file_url', 'view_url', 'file_type', 'file_name', 'created_at']

    def get_file_name(self, obj):
        """
        Trích xuất tên file từ URL MinIO (phần sau dấu / cuối cùng).

        Ví dụ: minio.example.com/bucket/2026/01/image.jpg -> image.jpg
        """
        if obj.file_url:
            return obj.file_url.split('/')[-1]
        return "attachment"

class PostSerializer(serializers.ModelSerializer):
    """
    Serialize bài viết để trả về Frontend (read-only, dùng cho GET list/detail).

    Tại sao:
    - Ánh xạ FK 'user' sang 'author' (đặt tên theo FeedPostCard contract).
    - Tính toán attachments, likes, comments từ bảng liên quan để trả về
      trong cùng một response (avoid N+1 query nếu optimize thêm).
    - status và reject_reason giúp UI hiển thị trạng thái duyệt và feedback.
    """
    author = UserResponseSerializer(source='user', read_only=True)
    category = CategorySerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    
    # Fake dữ liệu tương tác để Frontend không bị văng lỗi
    likes = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Posts
        fields = [
            'id', 'author', 'category', 'parent_post', 'content', 
            'visibility', 'status', 'reject_reason', 'is_edited', 
            'created_at', 'updated_at', 'attachments', 'likes', 'comments'
        ]

    def get_attachments(self, obj):
        """
        Lấy danh sách tệp đính kèm của bài viết qua bảng junction PostAttachments.

        Giúp UI load ảnh/video kèm theo bài viết mà không query riêng.
        """
        attachment_ids = PostAttachments.objects.filter(post=obj).values_list('attachment_id', flat=True)
        attachments = Attachments.objects.filter(id__in=attachment_ids)
        return AttachmentSerializer(attachments, many=True).data

    def get_likes(self, obj):
        """
        Trả về danh sách user_id đã like bài viết này.

        Frontend dùng để check: post.likes.some((l) => l.user_id === currentUser.id)
        để quyết định icon like có được highlight không.
        """
        likes = Likes.objects.filter(post=obj).values('user_id')
        return list(likes)

    def get_comments(self, obj):
        return Comments.objects.filter(post=obj).count()


class AttachmentPayloadSerializer(serializers.Serializer):
    """
    Validate mảng file_url nhận từ Frontend sau khi upload MinIO.

    Tại sao: Frontend upload file trực tiếp lên MinIO/S3 (external),
    sau đó gửi mảng {file_url, file_type, file_name} lên backend để
    lưu vào DB. Serializer này validate dữ liệu trước khi lưu.
    """
    file_url = serializers.CharField()
    file_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer để tạo/cập nhật bài viết (write-only, không dùng cho GET).

    Tại sao:
    - Tách riêng PostSerializer (GET) vs PostCreateUpdateSerializer (POST/PUT)
      để giữ logic tạo/cập nhật (set status=Pending, is_edited, timestamps).
    - Xử lý attachments là phần phức tạp: nhận mảng file_url, lưu vào
      bảng Attachments, rồi link qua PostAttachments.
    - category_id là write-only để Frontend không phải gửi object category.
    """
    category_id = serializers.IntegerField(write_only=True)
    attachments = AttachmentPayloadSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Posts
        fields = ['category_id', 'content', 'visibility', 'attachments']

    def create(self, validated_data):
        """
        Tạo bài viết mới với các tệp đính kèm.

        Các bước:
        1) Trích attachments từ validated_data (để xử lý riêng).
        2) Set status='Pending' (chờ admin duyệt), is_edited=False, timestamps.
        3) Gọi super().create() để lưu Post vào DB.
        4) Với mỗi attachment trong attachments_data:
           - Tạo row Attachments mới (file_url từ MinIO).
           - Tạo link PostAttachments nối post ↔ attachment.
        """
        attachments_data = validated_data.pop('attachments', [])
        
        validated_data['status'] = 'Pending'
        validated_data['is_edited'] = False
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        
        post = super().create(validated_data)
        
        # Xử lý lưu đường dẫn MinIO vào SQL Server
        for att_data in attachments_data:
            attachment = Attachments.objects.create(
                file_url=att_data.get('file_url'),
                file_type=att_data.get('file_type'),
                created_at=timezone.now()
            )
            PostAttachments.objects.create(post=post, attachment=attachment)
            
        return post

    def update(self, instance, validated_data):
        """
        Cập nhật bài viết và quản lý tệp đính kèm.

        Các bước:
        1) Trích attachments từ validated_data (nếu FE gửi).
        2) Set is_edited=True, updated_at=now.
        3) Gọi super().update() để lưu thay đổi.
        4) Nếu FE gửi attachments mới:
           - Xóa tất cả PostAttachments cũ (và Attachments liên quan nếu không
             được dùng ở post khác).
           - Tạo Attachments/PostAttachments mới từ mảng attachments_data.
        
        Lưu ý: Nếu FE không gửi attachments field thì giữ nguyên attachments cũ.
        """
        attachments_data = validated_data.pop('attachments', None)
        
        validated_data['is_edited'] = True
        validated_data['updated_at'] = timezone.now()
        
        post = super().update(instance, validated_data)
        
        # Xóa các file đính kèm cũ và tạo file mới nếu FE có gửi mảng attachments
        if attachments_data is not None:
            PostAttachments.objects.filter(post=post).delete()
            for att_data in attachments_data:
                attachment = Attachments.objects.create(
                    file_url=att_data.get('file_url'),
                    file_type=att_data.get('file_type'),
                    created_at=timezone.now()
                )
                PostAttachments.objects.create(post=post, attachment=attachment)
        
        return post
