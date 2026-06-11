"""
Serializers cho module Posts (Bài viết, bình luận).

Module này định nghĩa các DRF Serializer để:
- Serialize/deserialize bài viết (POST create/update, GET list/detail)
- Ánh xạ FK (user -> author) để khớp Frontend contract
- Tính toán các trường hợp lệ (likes count, comments count)
"""

from rest_framework import serializers
from apps.posts.models import Posts, Categories, Likes, Comments
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

class PostSerializer(serializers.ModelSerializer):
    """
    Serialize bài viết để trả về Frontend (read-only, dùng cho GET list/detail).

    Tại sao:
    - Ánh xạ FK 'user' sang 'author' (đặt tên theo FeedPostCard contract).
    - Tính toán likes, comments từ bảng liên quan để trả về
      trong cùng một response.
    - status và reject_reason giúp UI hiển thị trạng thái duyệt và feedback.
    """
    author = UserResponseSerializer(source='user', read_only=True)
    category = CategorySerializer(read_only=True)
    
    # Fake dữ liệu tương tác để Frontend không bị văng lỗi
    likes = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Posts
        fields = [
            'id', 'author', 'category', 'parent_post', 'content', 
            'visibility', 'status', 'reject_reason', 'is_edited', 
            'created_at', 'updated_at', 'likes', 'comments'
        ]

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

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer để tạo/cập nhật bài viết (write-only, không dùng cho GET).

    Tại sao:
    - Tách riêng PostSerializer (GET) vs PostCreateUpdateSerializer (POST/PUT)
      để giữ logic tạo/cập nhật (set status=Pending, is_edited, timestamps).
    - category_id là write-only để Frontend không phải gửi object category.
    """
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Posts
        fields = ['category_id', 'content', 'visibility']

    def create(self, validated_data):
        """
        Tạo bài viết mới.

        Các bước:
        1) Set status='Pending' (chờ admin duyệt), is_edited=False, timestamps.
        2) Gọi super().create() để lưu Post vào DB.
        """
        
        validated_data['status'] = 'Pending'
        validated_data['is_edited'] = False
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        
        post = super().create(validated_data)
        
        return post

    def update(self, instance, validated_data):
        """
        Cập nhật bài viết.

        Các bước:
        1) Set is_edited=True, updated_at=now.
        2) Gọi super().update() để lưu thay đổi.
        """
        
        validated_data['is_edited'] = True
        validated_data['updated_at'] = timezone.now()
        
        post = super().update(instance, validated_data)
        
        return post
