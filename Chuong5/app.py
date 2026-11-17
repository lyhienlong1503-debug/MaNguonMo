from datetime import timedelta
from flask import Flask, request, render_template, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email, ValidationError

app = Flask(__name__)
app.secret_key = "khoa_bi_mat_ung_dung_flask"
app.permanent_session_lifetime = timedelta(days=7)

# Cấu trúc lưu Users: {"username": {"password": "...", "email": "..."}}
Users = {
    "admin": {
        "password": "admin123",
        "email": "admin@gmail.com"
    }
}


# 1. Form Đăng nhập
class LoginForm(FlaskForm):
    username = StringField(
        "Tên đăng nhập",
        validators=[DataRequired(message="Vui lòng nhập tên đăng nhập!")],
        render_kw={"placeholder": "Nhập tên đăng nhập"},
    )
    password = PasswordField(
        "Mật khẩu",
        validators=[DataRequired(message="Vui lòng nhập mật khẩu!")],
        render_kw={"placeholder": "Nhập mật khẩu"},
    )
    remember = BooleanField("Ghi nhớ đăng nhập")
    submit = SubmitField("Đăng Nhập")


# 2. Form Đăng ký (Đã thêm trường Email)
class RegisterForm(FlaskForm):
    username = StringField(
        "Tên đăng nhập",
        validators=[
            DataRequired(message="Vui lòng nhập tên đăng nhập!"),
            Length(min=4, max=20, message="Tên đăng nhập phải từ 4 đến 20 ký tự!"),
        ],
        render_kw={"placeholder": "Từ 4 - 20 ký tự"},
    )
    email = StringField(
        "Địa chỉ Email",
        validators=[
            DataRequired(message="Vui lòng nhập email!"),
            Email(message="Địa chỉ email không đúng định dạng!"),
        ],
        render_kw={"placeholder": "example@gmail.com"},
    )
    password = PasswordField(
        "Mật khẩu",
        validators=[
            DataRequired(message="Vui lòng nhập mật khẩu!"),
            Length(min=8, message="Mật khẩu phải có ít nhất 8 ký tự!"),
        ],
        render_kw={"placeholder": "Ít nhất 8 ký tự"},
    )
    confirm_password = PasswordField(
        "Nhập lại mật khẩu",
        validators=[
            DataRequired(message="Vui lòng xác nhận mật khẩu!"),
            EqualTo("password", message="Mật khẩu nhập lại không khớp!"),
        ],
        render_kw={},
    )
    accept_terms = BooleanField(
        "Tôi đồng ý với các điều khoản dịch vụ và chính sách bảo mật",
        validators=[DataRequired(message="Bạn phải đồng ý với điều khoản dịch vụ để đăng ký!")]
    )
    submit = SubmitField("Đăng Ký Tài Khoản")

    def validate_username(self, field):
        ten = field.data.strip()
        if ten in Users:
            raise ValidationError("Tên đăng nhập này đã tồn tại! Vui lòng chọn tên khác.")

    def validate_email(self, field):
        email_nhap = field.data.strip()
        for user_info in Users.values():
            if user_info.get("email") == email_nhap:
                raise ValidationError("Email này đã được sử dụng bởi tài khoản khác!")


# Route /register
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("cal"))

    form = RegisterForm()

    if form.validate_on_submit():
        new_user = form.username.data.strip()
        new_email = form.email.data.strip()
        new_pass = form.password.data.strip()

        # Lưu vào từ điển Users
        Users[new_user] = {
            "password": new_pass,
            "email": new_email
        }
        flash(f"Đăng ký tài khoản '{new_user}' thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


# Route /login
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("cal"))

    form = LoginForm()

    if form.validate_on_submit():
        user_input = form.username.data.strip()
        pass_input = form.password.data.strip()
        remember_me = form.remember.data

        # Kiểm tra thông tin trong cấu trúc mới của Users
        if user_input in Users and Users[user_input]["password"] == pass_input:
            session.permanent = remember_me
            session["user"] = user_input
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for("cal"))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu!", "error")

    return render_template("login.html", form=form)


# Route /profile (Hiển thị thêm email của user đang đăng nhập)
@app.route("/profile")
def profile():
    if "user" not in session:
        flash("Vui lòng đăng nhập để xem trang hồ sơ cá nhân!", "error")
        return redirect(url_for("login"))

    current_user = session["user"]
    user_email = Users.get(current_user, {}).get("email", "Không có")

    return render_template("profile.html", user=current_user, email=user_email)


# Route /logout
@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("user", None)
    session.permanent = False
    flash("Bạn đã đăng xuất thành công.", "success")
    return redirect(url_for("login"))


# Trang chủ "/" (Máy tính cơ bản)
@app.route("/", methods=["GET", "POST"])
@app.route("/may-tinh", methods=["GET", "POST"])
def cal():
    result = None
    error = None
    a = request.form.get("a", "")
    b = request.form.get("b", "")
    op = request.form.get("op", "+")

    if request.method == "POST":
        if not a or not b:
            error = "Vui lòng nhập đủ 2 số!"
        else:
            try:
                num_a = float(a.strip().replace(",", "."))
                num_b = float(b.strip().replace(",", "."))

                if op == "+":
                    result = num_a + num_b
                elif op == "-":
                    result = num_a - num_b
                elif op == "*":
                    result = num_a * num_b
                elif op == "/":
                    if num_b == 0:
                        error = "Lỗi: Không thể chia cho 0!"
                    else:
                        result = num_a / num_b

                if result is not None and isinstance(result, float) and result.is_integer():
                    result = int(result)

            except ValueError:
                error = "Vui lòng nhập số hợp lệ!"

    return render_template("maytinh.html", result=result, error=error, a=a, b=b, op=op)


# Tính điểm học phần
@app.route("/tinh-diem", methods=["GET", "POST"])
def tinh_diem():
    dtb = None
    xep_loai = None
    error = None
    d1 = request.form.get("diem1", "")
    d2 = request.form.get("diem2", "")
    d3 = request.form.get("diem3", "")

    if request.method == "POST":
        try:
            diem1 = float(d1.strip().replace(",", "."))
            diem2 = float(d2.strip().replace(",", "."))
            diem3 = float(d3.strip().replace(",", "."))

            if not (0 <= diem1 <= 10 and 0 <= diem2 <= 10 and 0 <= diem3 <= 10):
                error = "Điểm phải nằm trong khoảng từ 0 đến 10!"
            else:
                dtb_val = diem1 * 0.1 + diem2 * 0.3 + diem3 * 0.6
                dtb = f"{dtb_val:.1f}"

                if diem3 < 1:
                    xep_loai = "F (Điểm thi dưới 1)"
                elif dtb_val >= 8.5:
                    xep_loai = "A"
                elif dtb_val >= 7.0:
                    xep_loai = "B"
                elif dtb_val >= 5.5:
                    xep_loai = "C"
                elif dtb_val >= 4.0:
                    xep_loai = "D"
                else:
                    xep_loai = "F"

        except ValueError:
            error = "Vui lòng nhập một số hợp lệ!"

    return render_template(
        "index.html",
        ket_qua=(dtb is not None),
        dtb=dtb,
        xep_loai=xep_loai,
        error=error,
        d1=d1,
        d2=d2,
        d3=d3,
    )


# Tính chỉ số BMI
@app.route("/tinh-BMI", methods=["GET", "POST"])
def tinh_BMI():
    bmi = None
    loai = None
    mau = ""
    error = None
    chieu_cao = request.form.get("chieu_cao", "")
    can_nang = request.form.get("can_nang", "")

    if request.method == "POST":
        try:
            cao = float(chieu_cao.strip().replace(",", "."))
            nang = float(can_nang.strip().replace(",", "."))

            if not (50 <= cao <= 250):
                error = "Chiều cao (cm) phải từ 50 đến 250!"
            elif not (10 <= nang <= 300):
                error = "Cân nặng (kg) phải từ 10 đến 300!"
            else:
                cao_met = cao / 100
                bmi_val = nang / (cao_met ** 2)
                bmi = f"{bmi_val:.1f}"

                if bmi_val < 18.5:
                    loai = "Thiếu cân (Vàng)"
                    mau = "yellow"
                elif bmi_val < 23.5:
                    loai = "Bình thường (Xanh)"
                    mau = "green"
                elif bmi_val < 25:
                    loai = "Thừa cân (Vàng)"
                    mau = "yellow"
                else:
                    loai = "Béo phì (Đỏ)"
                    mau = "red"

        except ValueError:
            error = "Vui lòng nhập một số hợp lệ!"

    return render_template(
        "bmi.html",
        ket_qua=(bmi is not None),
        bmi=bmi,
        loai=loai,
        mau=mau,
        error=error,
        chieu_cao=chieu_cao,
        can_nang=can_nang,
    )


if __name__ == "__main__":
    app.run(debug=True)