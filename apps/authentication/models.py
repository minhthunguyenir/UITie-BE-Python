from django.db import models

class Users(models.Model):
    """
    Mô hình người dùng cho hệ thống quản lý giáo dục.
    
    Lưu trữ thông tin xác thực, thông tin cá nhân và metadata của người dùng.
    Hỗ trợ các vai trò khác nhau (sinh viên, giáo viên, quản trị viên) với
    cơ chế kích hoạt/vô hiệu hóa tài khoản.
    """
    
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
    
    # Sử dụng email thay cho username để xác thực (tuân theo RFC 5321)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def is_authenticated(self):
        """
        Xác định tài khoản đã được xác thực hay chưa.
        
        Returns:
            bool: Luôn trả về True nếu object Users được tạo (có record trong DB).
                  Điều này giúp Django framework nhận diện user đã đăng nhập.
        """
        return True

    @property
    def is_anonymous(self):
        """
        Xác định đây có phải là tài khoản ẩn danh (khách) hay không.
        
        Returns:
            bool: Luôn trả về False vì mọi Users object đều là user thật,
                  không phải khách ẩn danh.
        """
        return False

    @property
    def is_active(self):
        """
        Kiểm tra tài khoản có đang hoạt động hay bị khóa.
        
        Phương pháp này cho phép quản trị viên kiểm soát quyền truy cập
        bằng cách cập nhật field 'status'. Nếu status là 'Active',
        user được phép đăng nhập và sử dụng hệ thống; nếu không sẽ bị khóa.
        
        Returns:
            bool: True nếu status = 'Active', False nếu không.
        """
        return self.status == 'Active'
    
    class Meta:
        managed = False
        db_table = 'users'
