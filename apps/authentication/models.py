from django.db import models

class Users(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.CharField(unique=True, max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    password = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    full_name = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS')
    mssv = models.CharField(unique=True, max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    phone_number = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    role = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    status = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')
    status_reason = models.TextField(db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    faculty = models.CharField(max_length=255, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    class_name = models.CharField(max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    academic_year = models.CharField(max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    remember_token = models.CharField(max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    USERNAME_FIELD = 'email'          # Chỉ định trường 'email' làm tên đăng nhập chính (thay cho 'username' mặc định của Django)
    REQUIRED_FIELDS = []              # Các trường bắt buộc phải nhập thêm khi tạo tài khoản bằng lệnh cmd (mình để trống là ok)

    @property
    def is_authenticated(self):
        """Trả về True để báo cho Django biết: Đây là tài khoản ĐÃ ĐĂNG NHẬP THÀNH CÔNG"""
        return True

    @property
    def is_anonymous(self):
        """Trả về False để khẳng định: Đây là người dùng thật, KHÔNG PHẢI KHÁCH ẨN DANH"""
        return False

    @property
    def is_active(self):
        """
        Bắt bài hệ thống: Tận dụng luôn cái trường 'status' của nhóm Thư.
        Nếu trạng thái là 'Active' thì trả về True (cho phép hoạt động), ngược lại thì khóa.
        """
        return self.status == 'Active'
    
    class Meta:
        managed = False
        db_table = 'users'
