"""
URL routing cho module Posts (Bài viết, bình luận, like, share).

Tại sao cấu trúc này:
- Tách POST endpoints (list/create, detail, like, share) để dễ quản lý
  phân quyền và moderation flow.
- Comment endpoints riêng để hỗ trợ nested reply (parent_comment).
- Like/Share là POST (không GET) để trigger business logic (create/delete,
  tạo notification, update moderation status).

URL Pattern:
  /posts/                       - GET/POST danh sách bài viết
  /posts/<id>                   - GET/PUT/DELETE chi tiết bài viết
  /posts/<id>/like              - POST/DELETE toggle like
  /posts/<id>/share             - POST tạo repost
  /posts/<id>/comments          - GET/POST danh sách bình luận
  /posts/comments/<id>          - GET/PUT/DELETE chi tiết bình luận
"""

from django.urls import path
from apps.posts.views import PostListCreateAPIView, PostDetailAPIView, PostLikeAPIView, PostShareAPIView, CommentListCreateAPIView, CommentDetailAPIView

# ========== BÀI VIẾT (Posts) ==========
# Tại sao tách riêng: cho phép quản lý CRUD, moderation, và tương tác
# (like/share) mà không gây xung đột logic trên cùng endpoint.

urlpatterns = [
    # POST list & create: danh sách tất cả bài viết hoặc tạo bài mới
    # Moderation: chỉ show bài status=Approved (ngoại trừ owner xem draft)
    path('', PostListCreateAPIView.as_view(), name='post_list_create_api'),
    
    # POST detail: xem/cập nhật/xóa một bài viết
    # Phân quyền: owner hoặc admin mới được sửa/xóa
    path('<int:pk>', PostDetailAPIView.as_view(), name='post_detail_api'),
    
    # POST like: toggle like trên bài viết
    # Tại sao POST (không GET): trigger side-effects (create/delete Likes row,
    # tạo Notification, update like count).
    path('<int:pk>/like', PostLikeAPIView.as_view(), name='post_like_api'),
    
    # POST share: tạo repost (parent_post -> original post)
    # Tại sao riêng endpoint: share là action đặc biệt (tạo post mới),
    # cần validate visibility & moderation rules riêng.
    path('<int:pk>/share', PostShareAPIView.as_view(), name='post_share_api'),
    
    # ========== BÌNH LUẬN (Comments) ==========
    # Tại sao tách: comment là nested entity (phụ thuộc vào post),
    # cần hỗ trợ parent_comment (reply), validation khác với post.
    
    # Comment list & create: danh sách bình luận của một bài viết
    # hoặc thêm bình luận mới (có thể reply bình luận khác qua parent_comment)
    path('<int:post_id>/comments', CommentListCreateAPIView.as_view(), name='post_comments_api'),
    
    # Comment detail: xem/cập nhật/xóa một bình luận
    # Phân quyền: owner hoặc admin xóa comment spam
    path('comments/<int:pk>', CommentDetailAPIView.as_view(), name='comment_detail_api'),
]

