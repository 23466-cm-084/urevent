from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename



app = Flask(__name__)

#-------For Displaying the event images------------
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


app.secret_key = "ur_events_secret_key"

DATABASE = "database.db"

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- CREATE DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # =========================
    # ADMIN TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # =========================
    # EVENTS TABLE (FINAL)
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        college TEXT,
        date TEXT,
        time TEXT,
        venue TEXT,
        description TEXT,
        category TEXT,
        image TEXT,
        featured INTEGER DEFAULT 0
    )
    """)

    # =========================
    # EVENT REGISTRATIONS TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        name TEXT,
        phone TEXT,
        email TEXT,
        message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events(id)
    )
    """)

    # =========================
    # CONTACT MESSAGES TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        subject TEXT,
        message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =========================
    # DEFAULT ADMIN INSERT
    # =========================
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO admin (username, password)
        VALUES (?, ?)
        """, ("admin", "admin123"))

    conn.commit()
    conn.close()


# ---------------- ROUTE For user to share their details----------------
@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register_event(event_id):
    conn = get_db_connection()
    event = conn.execute(
        "SELECT * FROM events WHERE id=?", (event_id,)
    ).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        message = request.form["message"]

        conn.execute("""
            INSERT INTO registrations
            (event_id, name, phone, email, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_id, name, phone, email, message, datetime.now()))

        conn.commit()
        conn.close()
        return redirect(url_for("thank_you"))

    conn.close()
    return render_template("register.html", event=event)

#------------Showed after Sharing the user Details------
@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


# ----------------  ROUTE allows admin to see the user details and contact them----------------
@app.route("/admin/registrations")
def admin_registrations():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    registrations = conn.execute("""
        SELECT registrations.id,
               registrations.name,
               registrations.phone,
               registrations.email,
               registrations.message,
               registrations.created_at,
               events.title AS event_title
        FROM registrations
        JOIN events ON registrations.event_id = events.id
        ORDER BY registrations.created_at DESC
    """).fetchall()
    conn.close()

    return render_template("admin_registrations.html", registrations=registrations)



# ---------------- HOME ROUTE ----------------
@app.route("/")
def home():
    conn = get_db_connection()

    featured_events = conn.execute("""
        SELECT * FROM events
        WHERE featured = 1
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    upcoming_events = conn.execute("""
        SELECT * FROM events
        ORDER BY date ASC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        "home.html",
        featured_events=featured_events,
        events=upcoming_events
    )



# ---------------- ABOUT US ROUTE ----------------
@app.route("/about")
def about():
    return render_template("about.html")



# ---------------- CONTACT US ROUTE ----------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name  = request.form["last_name"]
        email      = request.form["email"]
        phone      = request.form["phone"]
        subject    = request.form["subject"]
        message    = request.form["message"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contact_messages
            (first_name, last_name, email, phone, subject, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, subject, message))
        conn.commit()
        conn.close()

        flash("Message sent successfully!", "success")
        return redirect("/contact")

    return render_template("contact.html")


#---------To see the admin messages--------
@app.route("/admin/messages")
def admin_messages():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    messages = conn.execute("""
        SELECT * FROM contact_messages
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()

    return render_template("admin_messages.html", messages=messages)





# ---------------- ALL EVENTS ROUTE ----------------
@app.route("/events")
def all_events():
    conn = get_db_connection()
    events = conn.execute(
        "SELECT * FROM events ORDER BY date ASC"
    ).fetchall()
    conn.close()
    return render_template("all_events.html", events=events)



# ---------------- SINGLE EVENT ROUTE ----------------
@app.route("/event/<int:id>")
def event_detail(id):
    conn = get_db_connection()
    event = conn.execute(
        "SELECT * FROM events WHERE id=?", (id,)
    ).fetchone()
    conn.close()
    return render_template("event_detail.html", event=event)



# ---------------- ADMIN LOGIN ----------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        admin = conn.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if admin:
            if username == admin["username"] and password == admin["password"]:
                session["admin"] = True
                return redirect("/admin/dashboard")
            else:
                return "Invalid Login Credentials"

    return render_template("login.html")


# ---------------- ADMIN LOGOUT ----------------
@app.route("/admin/logout")
def admin_logout():
    session.clear()   # removes all session data
    return redirect(url_for("admin_login"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db_connection()
    events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", events=events)


# ---------------- ADD EVENT ----------------
@app.route("/admin/add-event", methods=["GET", "POST"])
def add_event():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        title = request.form["title"]
        college = request.form["college"]
        date = request.form["date"]
        time = request.form["time"]
        venue = request.form["venue"]
        description = request.form["description"]
        category = request.form["category"]
        featured = 1 if request.form.get("featured") else 0


        image_file = request.files["image"]
        image_filename = ""

        if image_file:
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
            image_file.save(image_path)

        conn = get_db_connection()
        conn.execute("""
        INSERT INTO events
        (title, college, date, time, venue, description, category, image, featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, college, date, time,
            venue, description, category,
            image_filename, featured
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("add_event.html")


# ---------------- UPDATE EVENT ----------------
@app.route("/admin/update/<int:id>", methods=["GET", "POST"])
def update_event(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    event = conn.execute(
        "SELECT * FROM events WHERE id=?", (id,)
    ).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        college = request.form["college"]
        date = request.form["date"]
        time = request.form["time"]
        venue = request.form["venue"]
        description = request.form["description"]
        category = request.form["category"]
        featured = 1 if request.form.get("featured") else 0


        # IMAGE UPDATE (optional)
        image_file = request.files["image"]
        image_filename = event["image"]

        if image_file and image_file.filename != "":
            image_filename = secure_filename(image_file.filename)
            image_file.save(
                os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
            )

        conn.execute("""
        UPDATE events SET
        title = ?, college = ?, date = ?, time = ?, venue = ?,
        description = ?, category = ?, image = ?, featured = ?
        WHERE id = ?
        """, (
            title, college, date, time, venue,
            description, category, image_filename,
            featured,id
            ))


        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("update_event.html", event=event)


# ---------------- DELETE EVENT ----------------
@app.route("/admin/delete/<int:id>")
def delete_event(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM events WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
