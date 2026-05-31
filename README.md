# UITie-BE-Python
# UITie - Backend API (Python/Django) 🚀

Hệ thống quản lý thông tin mạng xã hội (SMMS) - Đồ án môn học.
Backend được xây dựng bằng Python (Django REST Framework) và SQL Server.

## 🛠️ Công nghệ sử dụng
* **Ngôn ngữ:** Python 3.10+
* **Framework:** Django & Django REST Framework (DRF)
* **Cơ sở dữ liệu:** Microsoft SQL Server (chạy qua Docker)
* **Xác thực:** JWT (JSON Web Tokens)

---

## ⚙️ Hướng dẫn Cài đặt & Setup Môi trường

### 1. Yêu cầu hệ thống trước khi cài đặt (Prerequisites)
* Đã cài đặt **Python 3.10+**.
* Đã cài đặt **Docker Desktop** (để chạy SQL Server cục bộ).
* Cài đặt **ODBC Driver 18 for SQL Server** (Bắt buộc để kết nối CSDL):
  * **🖥️ Windows:** Tải và cài đặt file `.exe` trực tiếp từ [Trang chủ Microsoft](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).
  * **🍎 macOS:** Mở Terminal và chạy lệnh Homebrew:
    ```bash
    brew tap microsoft/mssql-release [https://github.com/Microsoft/homebrew-mssql-release](https://github.com/Microsoft/homebrew-mssql-release)
    brew update
    brew install msodbcsql18 mssql-tools18 unixodbc
    ```

### 2. Tải dự án và Khởi tạo môi trường ảo

Mở Terminal (macOS) hoặc Command Prompt/PowerShell (Windows) và chạy:

```bash
# Clone dự án về máy và chuyển sang nhánh phát triển
git clone [https://github.com/minhthunguyenir/UITie-BE-Python.git](https://github.com/minhthunguyenir/UITie-BE-Python.git)
cd UITie-BE-Python
git checkout develop

#Kích hoạt môi trường ảo (Virtual Environment):

🍎 Dành cho macOS:

python3 -m venv .venv
source .venv/bin/activate

🖥️ Dành cho Windows:

DOS
python -m venv .venv
.venv\Scripts\activate

```
### 3. Cài đặt Thư viện và Biến môi trường
Sau khi đầu dòng lệnh xuất hiện chữ (.venv), tiến hành cài đặt các gói phụ thuộc:

pip install -r requirements.txt

Cấu hình file .env: Copy nội dung từ file .env.example và tạo một file mới tên là .env nằm cùng thư mục gốc (ngang hàng manage.py).

Mở file .env và điền mật khẩu SQL Server của máy bạn vào biến DB_PASSWORD.


### 4. Khởi tạo Cơ sở dữ liệu (SQL Server)
Đảm bảo SQL Server đang chạy (thông qua Docker hoặc cài trực tiếp).

Dùng công cụ quản lý CSDL (VS Code mssql, SSMS, Azure Data Studio), kết nối bằng tài khoản sa.

Chạy lần lượt 3 file script trong thư mục database để dựng cấu trúc:

01_UITie_Python_Schema.sql

02_UITie_Python_Security.sql

03_UITie_Python_Permissions.sql

### 🚀 Hướng dẫn Thực thi chương trình (Run Server)
Tại thư mục gốc dự án (đã bật .venv), chạy lệnh sau để khởi động Backend:

🍎 macOS: python3 manage.py runserver
🖥️ Windows: python manage.py runserver

API sẽ được phục vụ tại địa chỉ: http://127.0.0.1:8000/

Dự án được phát triển bởi Nhóm UITie.