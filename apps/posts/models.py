from django.db import models
from apps.authentication.models import Users

class Attachments(models.Model):
    id = models.BigAutoField(primary_key=True)
    file_url = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS')
    file_type = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attachments'


class AuditLogs(models.Model):
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
    id = models.BigAutoField(primary_key=True)
    description = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    category_name = models.CharField(max_length=255, unique=True, db_collation='SQL_Latin1_General_CP1_CI_AS')

    class Meta:
        managed = False
        db_table = 'categories'


class CommentAttachments(models.Model):
    pk = models.CompositePrimaryKey('comment_id', 'attachment_id')
    comment = models.ForeignKey('Comments', models.DO_NOTHING)
    attachment = models.ForeignKey(Attachments, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'comment_attachments'


class Comments(models.Model):
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
    id = models.BigAutoField(primary_key=True)
    group_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_by = models.ForeignKey('authentication.Users', models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'group_chats'


class GroupMembers(models.Model):
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
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('authentication.Users', models.DO_NOTHING)
    post = models.ForeignKey('Posts', models.DO_NOTHING)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'likes'
        unique_together = (('user', 'post'),)


class MessageAttachments(models.Model):
    pk = models.CompositePrimaryKey('message_id', 'attachment_id')
    message = models.ForeignKey('Messages', models.DO_NOTHING)
    attachment = models.ForeignKey(Attachments, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'message_attachments'


class Messages(models.Model):
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


class PostAttachments(models.Model):
    pk = models.CompositePrimaryKey('post_id', 'attachment_id')
    post = models.ForeignKey('Posts', models.DO_NOTHING)
    attachment = models.ForeignKey(Attachments, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'post_attachments'


class Posts(models.Model):
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