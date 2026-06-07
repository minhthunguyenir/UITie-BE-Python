from rest_framework import serializers
from apps.posts.models import Posts, Categories, Attachments, PostAttachments, Likes, Comments
from apps.authentication.serializers import UserResponseSerializer
from django.utils import timezone

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = '__all__'

class AttachmentSerializer(serializers.ModelSerializer):
    # Frontend cần 'view_url' và 'file_name' để hiển thị ảnh/file đính kèm
    view_url = serializers.CharField(source='file_url', read_only=True)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Attachments
        fields = ['id', 'file_url', 'view_url', 'file_type', 'file_name', 'created_at']

    def get_file_name(self, obj):
        # Trích xuất tên file từ URL MinIO
        if obj.file_url:
            return obj.file_url.split('/')[-1]
        return "attachment"

class PostSerializer(serializers.ModelSerializer):
    # Map 'user' FK sang 'author' để khớp 100% với Frontend FeedPostCard
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
        # Lấy danh sách đính kèm qua bảng trung gian PostAttachments
        attachment_ids = PostAttachments.objects.filter(post=obj).values_list('attachment_id', flat=True)
        attachments = Attachments.objects.filter(id__in=attachment_ids)
        return AttachmentSerializer(attachments, many=True).data

    def get_likes(self, obj):
        # Frontend có hàm kiểm tra: post.likes.some((l) => l.user_id === user.id)
        likes = Likes.objects.filter(post=obj).values('user_id')
        return list(likes)

    def get_comments(self, obj):
        return Comments.objects.filter(post=obj).count()


class AttachmentPayloadSerializer(serializers.Serializer):
    """Bắt mảng JSON file_url từ Frontend gửi lên sau khi upload MinIO"""
    file_url = serializers.CharField()
    file_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True)
    attachments = AttachmentPayloadSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Posts
        fields = ['category_id', 'content', 'visibility', 'attachments']

    def create(self, validated_data):
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
