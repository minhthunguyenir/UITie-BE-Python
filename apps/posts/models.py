"""
Models cho module Posts (Bài viết, bình luận, theo dõi, thông báo).

Module này định nghĩa các Django model để quản lý:
- Bài viết (Posts), bình luận (Comments)
- Tương tác: Like, Follow, Report, Notification
- Chat nhóm và tin nhắn (GroupChats, Messages)
- Xác thực OTP (OtpVerification)
- Kiểm toán hoạt động (AuditLogs)
- Danh mục bài viết (Categories)

Tất cả model được cấu hình với managed=False vì DB đã tồn tại (legacy);
schema được quản lý bên ngoài Django migration.
"""

from django.db import models
from apps.authentication.models import Users


class AuditLogs(models.Model):
    """
    Ghi nhật ký hoạt động (INSERT/UPDATE/DELETE) trên bảng quan trọng.

    Tại sao: tuân thủ compliance và hỗ trợ điều tra lịch sử thay đổi
    (ai thay đổi cái gì lúc nào). Thiết kế trigger-based trên SQL Server.
    """
    log_id = models.AutoField(primary_key=True)
    table_name = models.CharField(max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')
    action = models.CharField(max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS')
    record_id = models.BigIntegerField(blank=True, null=True)
    old_data = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    new_data = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    executed_by = models.CharField(max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    executed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit_logs'


class Categories(models.Model):
    """
    Danh mục phân loại bài viết (Thông báo, Tuyển dụng, v.v.).

    Tại sao: cho phép admin định nghĩa các chủ đề/loại bài viết,
    giúp UI lọc/tìm kiếm theo category.
    """
    id = models.BigAutoField(primary_key=True)
    description = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    category_name = models.CharField(max_length=255, unique=True, db_collation='SQL_Latin1_General_CP1_CI_AS')

    class Meta:
        managed = False
        db_table = 'categories'


class Comments(models.Model):
    """
    Bình luận trên bài viết, hỗ trợ trả lời bình luận (reply nesting).

    Tại sao: parent_comment tạo quan hệ self-referential để xây dựng cây
    bình luận, cho phép users trả lời nhau trực tiếp.
    """
    id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey('Posts', models.DO_NOTHING)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    parent_comment = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    content = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comments'


class Follows(models.Model):
    """
    Quan hệ theo dõi (follow) giữa các user.

    Tại sao: dùng unique_together (follower, following) để tránh
    duplicate follow và hỗ trợ social feature (xem feeds người theo dõi).
    """
    id = models.BigAutoField(primary_key=True)
    follower = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    following = models.ForeignKey('authentication.Users', models.DO_NOTHING, related_name='follows_following_set')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'follows'
        unique_together = (('follower', 'following'),)


class GroupChats(models.Model):
    """
    Nhóm chat để gom nhóm tin nhắn của nhiều users.

    Tại sao: cho phép nhiều users chat cùng nhau; created_by ghi lại
    ai tạo nhóm để kiểm soát quyền admin/moderator nhóm.
    """
    id = models.BigAutoField(primary_key=True)
    group_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_by = models.ForeignKey('authentication.Users', models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'group_chats'


class GroupMembers(models.Model):
    """
    Thành viên của mỗi nhóm chat, với trạng thái (active, inactive).

    Tại sao: unique_together (group, user) đảm bảo mỗi user chỉ có
    một row trong nhóm; status theo dõi ai đang active/muted.
    """
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(GroupChats, models.DO_NOTHING)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    status = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    joined_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'group_members'
        unique_together = (('group', 'user'),)


class Likes(models.Model):
    """
    Lượt thích (Like) trên bài viết.

    Tại sao: unique_together (user, post) tránh duplicate like;
    cho phép UI hiển thị số lượt like và check user đã like hay chưa.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    post = models.ForeignKey('Posts', models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'likes'
        unique_together = (('user', 'post'),)



class Messages(models.Model):
    """
    Tin nhắn 1-on-1 hoặc group chat.

    Tại sao: receiver là NULL cho group messages (dùng group field);
    tách riêng sender/receiver/group cho phép cùng model hỗ trợ cả 2 loại chat.
    """
    id = models.BigAutoField(primary_key=True)
    sender = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    receiver = models.ForeignKey('authentication.Users', models.DO_NOTHING, related_name='messages_receiver_set', blank=True, null=True)
    group = models.ForeignKey(GroupChats, models.DO_NOTHING, blank=True, null=True)
    content = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'messages'


class Notifications(models.Model):
    """
    Thông báo cho user (like, comment, follow, post approval, v.v.).

    Tại sao: reference_id cho phép ghi lại bài viết/bình luận/user
    liên quan; type phân loại event để UI render icon/message khác nhau.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    content = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    type = models.CharField(max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    is_read = models.BooleanField()
    reference_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'


class OtpVerification(models.Model):
    """
    Mã OTP gửi qua email/SMS để xác thực các hành động nhạy cảm.

    Tại sao: theo dõi OTP type (reset password, email verification, v.v.)
    và trạng thái is_used để tránh tái sử dụng code sau khi đã xác thực.
    """
    otp_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    otp_code = models.CharField(max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS')
    otp_type = models.CharField(max_length=30, db_collation='SQL_Latin1_General_CP1_CI_AS')
    expired_at = models.DateTimeField(blank=True, null=True)
    is_used = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'otp_verification'


class Posts(models.Model):
    """
    Bài viết trên hệ thống (có thể là post chính hoặc share của bài khác).

    Tại sao:
    - status (Pending/Approved/Rejected) kiểm soát moderation flow.
    - visibility (Public/Private) ghi nhận quyền xem của bài viết.
    - parent_post hỗ trợ share/repost (cây bài viết).
    - is_edited và deleted_at theo dõi lịch sử (soft delete, edit flag).
    - reject_reason lưu feedback khi admin từ chối duyệt.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    category = models.ForeignKey(Categories, models.DO_NOTHING, blank=True, null=True)
    parent_post = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    content = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    visibility = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    status = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    reject_reason = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    is_edited = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'posts'


class Reports(models.Model):
    """
    Báo cáo vi phạm (spam, inappropriate content, harassment).

    Tại sao:
    - target_type (user / post) phân biệt báo cáo về người hay bài viết.
    - reported_user / reported_post: một cái NULL tùy target_type.
    - resolved_by ghi lại admin nào xử lý báo cáo này.
    - status (Open/Resolved/Dismissed) theo dõi quy trình xử lý.
    - resolved_at lưu dấu thời gian khi hoàn tất xử lý.
    """
    id = models.BigAutoField(primary_key=True)
    reporter = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    reported_user = models.ForeignKey('authentication.Users', models.DO_NOTHING, related_name='reports_reported_user_set', blank=True, null=True)
    reported_post = models.ForeignKey(Posts, models.DO_NOTHING, blank=True, null=True)
    resolved_by = models.ForeignKey('authentication.Users', models.DO_NOTHING, db_column='resolved_by', related_name='reports_resolved_by_set', blank=True, null=True)
    reason = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    status = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    target_type = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reports'