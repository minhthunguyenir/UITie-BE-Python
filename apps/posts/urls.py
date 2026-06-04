from django.urls import path
from apps.posts.views import PostListCreateAPIView, PostDetailAPIView

urlpatterns = [
    path('', PostListCreateAPIView.as_view(), name='post_list_create_api'),
    path('<int:pk>', PostDetailAPIView.as_view(), name='post_detail_api'),
]
