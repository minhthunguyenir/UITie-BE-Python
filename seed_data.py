import os
import django
import random

# Khởi tạo môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import IntegrityError
from django.contrib.auth.hashers import make_password
from faker import Faker

from apps.authentication.models import Users
from apps.posts.models import Categories, Posts, Comments

fake = Faker('vi_VN')

def seed_data():
    print("="*50)
    print("🚀 BẮT ĐẦU QUÁ TRÌNH TẠO DỮ LIỆU MẪU (SEED DATA)...")
    print("="*50)

    # 1. Tạo Categories
    print("\n⏳ Đang tạo 4 Categories...")
    category_names = ['Học tập', 'Đời sống', 'Hướng nghiệp', 'Hành chính']
    categories_list = []
    for name in category_names:
        try:
            category, created = Categories.objects.get_or_create(category_name=name)
            categories_list.append(category)
            if created:
                print(f"  [+] Đã tạo category: {name}")
            else:
                print(f"  [~] Category đã tồn tại: {name}")
        except Exception as e:
            print(f"  [x] Lỗi khi tạo category '{name}': {e}")

    # 2. Tạo Users
    print("\n⏳ Đang tạo 10 Users...")
    users_list = []
    for i in range(2, 12):
        mssv = f"215200{i:02d}"
        email = f"student{i:02d}@ms.uit.edu.vn"
        
        try:
            user, created = Users.objects.get_or_create(
                email=email,
                defaults={
                    'password': make_password('12345678'),
                    'full_name': fake.name(),
                    'mssv': mssv,
                    'role': 'Student',
                    'status': 'Active'
                }
            )
            users_list.append(user)
            if created:
                print(f"  [+] Đã tạo user: {email} (MSSV: {mssv})")
            else:
                print(f"  [~] User đã tồn tại: {email}")
        except IntegrityError:
            print(f"  [!] Bỏ qua User {email} do lỗi trùng lặp (IntegrityError).")
        except Exception as e:
            print(f"  [x] Lỗi khi tạo user {email}: {e}")

    # 3. Tạo Posts
    print("\n⏳ Đang tạo 10 Posts...")
    posts_list = []
    if not users_list or not categories_list:
        print("  [!] Thiếu dữ liệu Users hoặc Categories, bỏ qua tạo Posts.")
    else:
        for i in range(10):
            try:
                post = Posts.objects.create(
                    content=fake.paragraph(nb_sentences=5),
                    category=random.choice(categories_list),
                    user=random.choice(users_list),
                    visibility='Public',
                    status='Accepted',  # Thay giá trị này bằng giá trị hợp lệ mà bạn tìm thấy trong CSDL
                    is_edited=False
                )
                posts_list.append(post)
                print(f"  [+] Đã tạo Post #{post.id} bởi tác giả {post.user.email}")
            except Exception as e:
                print(f"  [x] Lỗi khi tạo Post: {e}")

    # 4. Tạo Comments
    print("\n⏳ Đang tạo 10 Comments...")
    if not posts_list or not users_list:
        print("  [!] Thiếu dữ liệu Posts hoặc Users, bỏ qua tạo Comments.")
    else:
        for i in range(10):
            try:
                comment = Comments.objects.create(
                    content=fake.sentence(nb_words=15),
                    post=random.choice(posts_list),
                    user=random.choice(users_list)
                )
                print(f"  [+] Đã tạo Comment #{comment.id} trên Post #{comment.post.id}")
            except Exception as e:
                print(f"  [x] Lỗi khi tạo Comment: {e}")

    print("\n🎉 HOÀN TẤT QUÁ TRÌNH TẠO DỮ LIỆU MẪU!")

if __name__ == '__main__':
    seed_data()
