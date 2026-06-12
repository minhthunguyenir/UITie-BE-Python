# UITie - Mạng Xã Hội Nội Bộ Sinh Viên (Campus Social Network)

UITie là hệ thống mạng xã hội nội bộ dành riêng cho môi trường đại học, hỗ trợ sinh viên kết nối, chia sẻ tài liệu, cập nhật hoạt động Đoàn - Hội và thảo luận học tập. Hệ thống được trang bị phân hệ **Admin Console** toàn diện giúp quản trị viên kiểm duyệt nội dung thông minh, quản lý trạng thái người dùng và theo dõi sức khỏe hệ thống qua Dashboard số liệu thời gian thực.

---

## Công Nghệ Sử Dụng

### Backend
* **Ngôn ngữ:** Python 3.11+
* **Framework:** Django & Django REST Framework (DRF)
* **Cơ sở dữ liệu:** Microsoft SQL Server (kết nối qua kết cấu Django ORM)
* **Xác thực:** JWT (JSON Web Token) qua `rest_framework_simplejwt`

### Frontend
* **Ngôn ngữ:** TypeScript
* **Framework:** React & TanStack Start / Router
* **Quản lý State & Call API:** TanStack Query (`@tanstack/react-query`)
* **Styling:** TailwindCSS

---

## 📋 Yêu Cầu Hệ Thống (Prerequisites)

Trước khi tiến hành cài đặt, hãy đảm bảo máy tính đã cài đặt các công cụ sau:
* **Python** (Phiên bản >= 3.11)
* **Node.js** (Phiên bản >= 18.x) & **npm**
* **Microsoft SQL Server** (2019 hoặc mới hơn)
* **Microsoft ODBC Driver for SQL Server** (Thư viện kết nối bắt buộc cho Python)

---

## Hướng Dẫn Cài Đặt Chi Tiết

### 1. Tải Mã Nguồn Về Máy
```bash
git clone [https://github.com/minhthunguyenir/UITie-BE-Python.git](https://github.com/minhthunguyenir/UITie-BE-Python.git)
cd UITie-BE-Python
```

### 2. Cấu Hình & Chạy Backend (Django)

**Bước 2.1: Tạo và kích hoạt môi trường ảo (Virtual Environment)**
* **Trên macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
* **Trên Windows:**
  ```cmd
  python -m venv venv
  .\\venv\\Scripts\\activate
  ```

**Bước 2.2: Cài đặt các thư viện phụ thuộc**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Bước 2.3: Cấu hình file môi trường `.env`**
Tạo file `.env` tại thư mục gốc của Backend (ngang hàng với `manage.py`) dựa trên file `.env.example`:
```env
DEBUG=True
SECRET_KEY=django-insecure-your-custom-secret-key-uitie
DB_NAME=UITie_DB
DB_USER=sa
DB_PASSWORD=YourStrongPassword123
DB_HOST=127.0.0.1
DB_PORT=1433
```

**Bước 2.4: Thực thi Khởi tạo Cơ sở dữ liệu (Migrations & Seed Data)**
```bash
# Tạo cấu trúc bảng trên SQL Server
python manage.py migrate

# (Tùy chọn) Chạy lệnh nạp dữ liệu mẫu sinh viên và bài viết nếu nhóm có viết lệnh seed
python manage.py seed_data
```

**Bước 2.5: Khởi chạy Server Backend**
```bash
python manage.py runserver 0.0.0.0:8000
```
> Server Backend sẽ chạy tại cổng: `http://127.0.0.1:8000/`

---

### 3. Cấu Hình & Chạy Frontend (React / TanStack Start)

Mở một cửa sổ Terminal mới và di chuyển vào thư mục Frontend của dự án:

**Bước 3.1: Cài đặt các gói thư viện Node Modules**
```bash
cd frontend
npm install
```

**Bước 3.2: Cấu hình file môi trường Frontend**
Tạo file `.env` tại thư mục gốc của Frontend:
```env
VITE_API_BASE_URL=[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
```

**Bước 3.3: Khởi chạy Server Frontend ở chế độ Phát triển (Development)**
```bash
npm run dev
```
> Giao diện người dùng sẽ chạy tại cổng mặc định: `http://localhost:3000/`
