import sqlite3
from contextlib import closing
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "oss_secret_key_2026"
DB_NAME = "library.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 1,
    published_year INTEGER,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
);
"""

CATEGORIES_SQL = """
    SELECT c.*, COUNT(b.id) AS book_count
    FROM categories c LEFT JOIN books b ON c.id = b.category_id
    GROUP BY c.id ORDER BY c.id DESC
"""
BOOKS_SQL = """
    SELECT b.*, c.name AS category_name
    FROM books b JOIN categories c ON b.category_id = c.id
"""


# ---------- Tiện ích CSDL ----------

def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, args=(), one=False):
    """Chạy SELECT, trả về danh sách dòng (hoặc 1 dòng nếu one=True)."""
    with closing(connect()) as conn:
        rows = conn.execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=(), renumber=None):
    """Chạy lệnh ghi trong 1 transaction. renumber=(bảng, (bảng_con, cột_khóa_ngoại))
    sẽ đánh lại id 1, 2, 3... sau khi chạy lệnh (dùng khi xóa)."""
    with closing(connect()) as conn:
        try:
            conn.execute(sql, args)
            if renumber:
                renumber_ids(conn, *renumber)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def renumber_ids(conn, table, child=None):
    """Đánh lại id của `table` thành 1, 2, 3... và cập nhật khóa ngoại ở bảng con."""
    conn.execute("PRAGMA defer_foreign_keys = ON")  # hoãn kiểm tra khóa ngoại đến lúc commit
    ids = [r[0] for r in conn.execute(f"SELECT id FROM {table} ORDER BY id")]
    for new_id, old_id in enumerate(ids, start=1):
        if new_id != old_id:
            conn.execute(f"UPDATE {table} SET id = ? WHERE id = ?", (new_id, old_id))
            if child:
                child_table, fk = child
                conn.execute(f"UPDATE {child_table} SET {fk} = ? WHERE {fk} = ?", (new_id, old_id))
    conn.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (len(ids), table))


def init_db():
    """Tạo bảng và chèn dữ liệu mẫu nếu CSDL đang trống."""
    with closing(connect()) as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            conn.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", [
                ("Công nghệ thông tin", "Sách lập trình, mạng máy tính, AI, mã nguồn mở"),
                ("Kinh tế - Quản trị", "Sách khởi nghiệp, tài chính, quản trị kinh doanh"),
                ("Văn học", "Tiểu thuyết, truyện ngắn trong và ngoài nước"),
                ("Kỹ năng sống", "Sách phát triển bản thân, giao tiếp"),
            ])
            conn.executemany(
                "INSERT INTO books (title, author, price, stock, published_year, category_id) "
                "VALUES (?, ?, ?, ?, ?, ?)", [
                    ("Lập trình Python Mã nguồn mở", "Nguyễn Văn A", 145000, 15, 2025, 1),
                    ("Làm chủ Linux & Docker", "Trần Thị B", 180000, 10, 2024, 1),
                    ("Quản trị Dự án Agile", "Lê Văn C", 120000, 8, 2023, 2),
                    ("Nhà Giả Kim", "Paulo Coelho", 79000, 25, 2020, 3),
                    ("Đắc Nhân Tâm", "Dale Carnegie", 86000, 30, 2022, 4),
                ])
            conn.commit()


# ---------- Dashboard ----------

@app.route("/")
def dashboard():
    total_categories, total_books, total_stock = query(
        "SELECT (SELECT COUNT(*) FROM categories), (SELECT COUNT(*) FROM books), "
        "(SELECT COALESCE(SUM(stock), 0) FROM books)", one=True)
    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_books=total_books,
        total_stock=total_stock,
        category_stats=query(CATEGORIES_SQL),
        recent_books=query(BOOKS_SQL + " ORDER BY b.id DESC LIMIT 8"),
    )


# ---------- CRUD Danh mục ----------

@app.route("/categories")
def list_categories():
    edit_id = request.args.get("edit_id", type=int)
    edit_category = query("SELECT * FROM categories WHERE id = ?", (edit_id,), one=True) if edit_id else None
    return render_template("categories.html", categories=query(CATEGORIES_SQL), edit_category=edit_category)


@app.route("/categories/save", methods=["POST"])
def save_category():
    cat_id = request.form.get("id", type=int)
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Tên danh mục không được để trống!", "danger")
        return redirect(url_for("list_categories"))

    try:
        if cat_id:
            execute("UPDATE categories SET name = ?, description = ? WHERE id = ?", (name, description, cat_id))
            flash("Đã cập nhật danh mục thành công!", "success")
        else:
            execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, description))
            flash("Đã thêm danh mục mới thành công!", "success")
    except sqlite3.IntegrityError:
        flash("Tên danh mục này đã tồn tại!", "danger")
    return redirect(url_for("list_categories"))


@app.route("/categories/delete/<int:id>", methods=["POST"])
def delete_category(id):
    try:
        execute("DELETE FROM categories WHERE id = ?", (id,), renumber=("categories", ("books", "category_id")))
        flash("Đã xóa danh mục thành công!", "success")
    except sqlite3.IntegrityError:
        flash("Không thể xóa danh mục này vì đang có sách thuộc danh mục!", "danger")
    return redirect(url_for("list_categories"))


# ---------- CRUD Sách ----------

@app.route("/books")
def list_books():
    category_id = request.args.get("category_id", type=int)
    keyword = request.args.get("q", "").strip()

    sql, params = BOOKS_SQL + " WHERE 1=1", []
    if category_id:
        sql += " AND b.category_id = ?"
        params.append(category_id)
    if keyword:
        sql += " AND (b.title LIKE ? OR b.author LIKE ?)"
        params += [f"%{keyword}%"] * 2

    return render_template(
        "books.html",
        books=query(sql + " ORDER BY b.id DESC", params),
        categories=query("SELECT * FROM categories ORDER BY name"),
        selected_category=category_id,
        keyword=keyword,
    )


@app.route("/books/create", methods=["GET", "POST"])
@app.route("/books/edit/<int:id>", methods=["GET", "POST"])
def save_book(id=None):
    book = query("SELECT * FROM books WHERE id = ?", (id,), one=True) if id else None
    if id and not book:
        flash("Không tìm thấy sách!", "danger")
        return redirect(url_for("list_books"))

    if request.method == "POST":
        f = request.form
        data = (
            f.get("title", "").strip(),
            f.get("author", "").strip(),
            f.get("price", type=float, default=0.0),
            f.get("stock", type=int, default=0),
            f.get("published_year", type=int),
            f.get("category_id", type=int),
        )
        title, author, price, stock, _, category_id = data

        if not (title and author and category_id):
            flash("Vui lòng nhập đầy đủ Tên sách, Tác giả và Danh mục!", "danger")
        elif price < 0 or stock < 0:
            flash("Giá sách và Số lượng tồn không được âm!", "danger")
        else:
            if id:
                execute("UPDATE books SET title = ?, author = ?, price = ?, stock = ?, "
                        "published_year = ?, category_id = ? WHERE id = ?", data + (id,))
                flash("Cập nhật thông tin sách thành công!", "success")
            else:
                execute("INSERT INTO books (title, author, price, stock, published_year, category_id) "
                        "VALUES (?, ?, ?, ?, ?, ?)", data)
                flash("Thêm sách mới thành công!", "success")
            return redirect(url_for("list_books", category_id=category_id))

    return render_template(
        "book_form.html",
        book=book,
        categories=query("SELECT * FROM categories ORDER BY name"),
        default_cat=request.args.get("category_id", type=int),
    )


@app.route("/books/delete/<int:id>", methods=["POST"])
def delete_book(id):
    execute("DELETE FROM books WHERE id = ?", (id,), renumber=("books",))
    flash("Đã xóa sách khỏi hệ thống!", "success")
    return redirect(url_for("list_books"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)