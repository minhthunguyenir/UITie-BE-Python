from django.urls import path
from apps.posts.views import PostListCreateAPIView, PostDetailAPIView, PostLikeAPIView, PostShareAPIView, CommentListCreateAPIView, CommentDetailAPIView

urlpatterns = [
    path('', PostListCreateAPIView.as_view(), name='post_list_create_api'),
    path('<int:pk>', PostDetailAPIView.as_view(), name='post_detail_api'),
    path('<int:pk>/like', PostLikeAPIView.as_view(), name='post_like_api'),
    path('<int:pk>/share', PostShareAPIView.as_view(), name='post_share_api'),
    path('<int:post_id>/comments', CommentListCreateAPIView.as_view(), name='post_comments_api'),
    path('comments/<int:pk>', CommentDetailAPIView.as_view(), name='comment_detail_api'),
]
