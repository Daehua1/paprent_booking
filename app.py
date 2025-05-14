from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def init_db():
    with sqlite3.connect("bookings.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                date TEXT NOT NULL,
                class TEXT NOT NULL,
                confirmed INTEGER DEFAULT 0
            )
        ''')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("관리자 로그인이 필요합니다.")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        time_slot = request.form["time_slot"]
        date = request.form["date"]
        class_name = request.form["class"]

        with sqlite3.connect("bookings.db") as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM bookings WHERE date = ? AND time_slot = ? AND class = ?", (date, time_slot, class_name))
            if cur.fetchone()[0] > 0:
                return "❗ 이미 해당 날짜, 시간, 반에 예약이 있습니다."
            conn.execute("INSERT INTO bookings (name, phone, time_slot, date, class, confirmed) VALUES (?, ?, ?, ?, ?, 0)",
                         (name, phone, time_slot, date, class_name))
        return redirect("/success")
    return render_template("index.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/check", methods=["GET", "POST"])
def check():
    booking = None
    if request.method == "POST":
        phone = request.form["phone"]
        with sqlite3.connect("bookings.db") as conn:
            cur = conn.cursor()
            cur.execute("SELECT name, date, class, time_slot, confirmed FROM bookings WHERE phone = ?", (phone,))
            row = cur.fetchone()
            if row:
                booking = {
                    "name": row[0],
                    "date": row[1],
                    "class": row[2],
                    "time_slot": row[3],
                    "confirmed": row[4]
                }
            else:
                booking = False
    return render_template("check.html", booking=booking)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        flash("❌ 아이디 또는 비밀번호가 틀렸습니다.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    start_date = request.form.get("start_date") if request.method == "POST" else ""
    end_date = request.form.get("end_date") if request.method == "POST" else ""

    query = "SELECT id, name, phone, date, class, time_slot, confirmed FROM bookings"
    params = []

    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif start_date:
        query += " WHERE date >= ?"
        params.append(start_date)
    elif end_date:
        query += " WHERE date <= ?"
        params.append(end_date)

    query += " ORDER BY date, time_slot, class"

    with sqlite3.connect("bookings.db") as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        bookings = cur.fetchall()

        statistics = {}
        for i in range(1, 11):
            cls = f"{i}반"
            cur.execute("SELECT COUNT(*) FROM bookings WHERE class = ?", (cls,))
            statistics[cls] = cur.fetchone()[0]

    return render_template("admin.html", bookings=bookings, statistics=statistics,
                           start_date=start_date, end_date=end_date)

@app.route("/confirm/<int:booking_id>", methods=["POST"])
@login_required
def confirm_booking(booking_id):
    with sqlite3.connect("bookings.db") as conn:
        conn.execute("UPDATE bookings SET confirmed = 1 WHERE id = ?", (booking_id,))
    return redirect("/admin")

@app.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    with sqlite3.connect("bookings.db") as conn:
        conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    return redirect("/admin")

init_db()  # ← 조건문 밖으로 빼기!

if __name__ == "__main__":
    app.run()
