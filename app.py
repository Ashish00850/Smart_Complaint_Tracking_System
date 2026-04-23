from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import random
import smtplib
import time
import os
from email.mime.text import MIMEText

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123" 

app = Flask(__name__)
app.secret_key = "1623"

# Database connection
try:
    db = mysql.connector.connect(
        host="shortline.proxy.rlwy.net",
        user="root",
        password="MTCboVLqnYEZtFlAHLCasXuGvKUrxGFm",
        database="railway",
        port=3306
    )
    cursor = db.cursor()
    print("DB Connected Successfully")

except Exception as e:
    print("DB Connection Error:", e)
# Login page
@app.route("/")
def home():
    return render_template("login.html")


# Login authentication
@app.route("/login", methods=["GET","POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]
        cursor = db.cursor(buffered=True)

        query = "SELECT * FROM users WHERE email=%s AND password=%s"
        cursor.execute(query,(email,password))

        user = cursor.fetchone()

        if user:

            session["email"] = user[2]
            session["name"] = user[1]

            return redirect("/dashboard")

        else:
            error = "Invalid Email or Password"

    return render_template("login.html", error=error)


# Registration page
@app.route("/register")
def register_page():
    return render_template("registration.html")

def send_otp_email(receiver_email, otp):
    sender_email = "quickresolve1@gmail.com"
    app_password = "dyhnegcygqgiceha"

    subject = "OTP Verification"
    body = f"Your OTP for Smart Complaint System registration is: {otp}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("OTP sent successfully")
    except Exception as e:
        print("Email error:", e)

# Register user
@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"].strip()
    roll_no = request.form["roll_no"].strip()
    email = request.form["email"].strip()
    password = request.form["password"].strip()
    phone = request.form["phone"].strip()

    # Check authorized student
    cursor.execute(
    "SELECT * FROM college_students WHERE roll_no=%s AND mobile=%s",
    (roll_no, phone)
    )

    student = cursor.fetchone()
    print("Student found:", student)   # debug

    if not student:
        flash("You are not an authorized college student")
        return redirect("/register")

    cursor.execute(
    "SELECT * FROM users WHERE roll_no=%s OR email=%s",
    (roll_no, email)
    )

    existing = cursor.fetchone()

    if existing:
        flash("Student already registered with this roll number or email !")
        return redirect("/register")

    if existing:
        flash("This student is already registered")
        return redirect("/register")

    # Generate OTP
    otp = random.randint(100000, 999999)
    session["otp"] = str(otp)
    session["otp_time"] = time.time()

    # Save data temporarily in session
    session["otp"] = str(otp)
    session["name"] = name
    session["roll_no"] = roll_no
    session["email"] = email
    session["password"] = password
    session["phone"] = phone

    # Send OTP
    send_otp_email(email, otp)

    flash("OTP sent to your email")
    return redirect("/verify_otp")

import time

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":
        user_otp = request.form["otp"]

        print("Entered OTP:", user_otp)
        print("Session OTP:", session.get("otp"))

        # OTP expiry check (2 minutes = 120 sec)
        if time.time() - session.get("otp_time", 0) > 120:
            flash("OTP expired! Please click resend OTP.")
            return redirect("/verify_otp")

        # OTP match check
        if user_otp == session.get("otp"):
            print("OTP matched")

            # Extra duplicate email check
            cursor.execute(
                "SELECT * FROM users WHERE email=%s",
                (session["email"],)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Email already registered")
                return redirect("/register")

            # Insert user after successful OTP verification
            cursor.execute(
                "INSERT INTO users (name, roll_no, email, password, phone) VALUES (%s,%s,%s,%s,%s)",
                (
                    session["name"],
                    session["roll_no"],
                    session["email"],
                    session["password"],
                    session["phone"]
                )
            )
            db.commit()

            # Clear OTP/session data
            session.pop("otp", None)
            session.pop("otp_time", None)

            print("Registration completed")

            return render_template(
                "otp_success.html",
                message="OTP verified successfully! Please login."
            )

        else:
            print("OTP mismatch")
            flash("Invalid OTP")

    return render_template("verify_otp.html")

@app.route("/resend_otp", methods=["POST"])
def resend_otp():

    otp = random.randint(100000, 999999)

    session["otp"] = str(otp)
    session["otp_time"] = time.time()

    send_otp_email(session["email"], otp)

    flash("New OTP sent successfully!")
    return redirect("/verify_otp")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        # Send OTP
        if "send_otp" in request.form:
            email = request.form["email"]

            cursor.execute(
                "SELECT * FROM users WHERE email=%s",
                (email,)
            )
            user = cursor.fetchone()

            if not user:
                flash("Email not registered")
                return redirect("/forgot_password")

            otp = random.randint(100000, 999999)

            session["reset_email"] = email
            session["reset_otp"] = str(otp)
            session["otp_time"] = time.time()
            session["otp_verified"] = False

            send_otp_email(email, otp)

            flash("OTP sent to your email")
            return redirect("/forgot_password")

        # Verify OTP
        elif "verify_otp" in request.form:
            entered_otp = request.form["otp"]
            session["reset_otp_entered"] = entered_otp

            if entered_otp == session.get("reset_otp"):
                session["otp_verified"] = True
                flash("OTP verified successfully")

            else:
                flash("Invalid OTP")

        # Update Password
        elif "update_password" in request.form:

            if not session.get("otp_verified"):
                flash("Please verify OTP first")
                return redirect("/forgot_password")

            new_password = request.form["new_password"]

            cursor.execute(
                "UPDATE users SET password=%s WHERE email=%s",
                (new_password, session["reset_email"])
            )
            db.commit()

            session.pop("reset_email", None)
            session.pop("reset_otp", None)
            session.pop("otp_time", None)
            session.pop("otp_verified", None)
            session.pop("reset_otp_entered", None)

            return render_template("password_success.html")

    return render_template("forgot_password.html")


@app.route("/verify_reset_otp", methods=["GET", "POST"])
def verify_reset_otp():

    if request.method == "POST":
        user_otp = request.form["otp"]

        if time.time() - session.get("otp_time", 0) > 120:
            flash("OTP expired")
            return redirect("/forgot_password")

        if user_otp == session.get("reset_otp"):
            return redirect("/reset_password")

        else:
            flash("Invalid OTP")

    return render_template("verify_reset_otp.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if request.method == "POST":
        new_password = request.form["new_password"]

        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password, session["reset_email"])
        )
        db.commit()

    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_time", None)

    return render_template(
    "password_success.html",
    message="Password updated successfully! Please login."
    )
    return render_template("reset_password.html")


@app.route("/dashboard")
def dashboard():

    name = session["name"]

    return render_template("dashboard.html", name=name) 

@app.route("/complaint")
def complaint():
    return render_template("complaint.html")

@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    email = session["email"]
    name = session["name"]

    category = request.form["category"]
    subject = request.form["subject"]
    description = request.form["description"]

    query = """INSERT INTO complaints
    (name,user_email,category,subject,description)
    VALUES (%s,%s,%s,%s,%s)"""

    values = (name,email,category,subject,description)

    cursor.execute(query, values)
    db.commit()

    flash("Your complaint has been submitted successfully!")
    return redirect("/dashboard")

@app.route("/view_complaints")
def view_complaints():

    email = session["email"]

    query = "SELECT * FROM complaints WHERE user_email=%s"
    cursor.execute(query,(email,))

    complaints = cursor.fetchall()

    return render_template("view_complaints.html", complaints=complaints) 


@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin_login")

    return redirect("/admin_interface")

@app.route('/admin_interface')
def admin_interface():
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]



    return render_template("admin_interface.html",
                           total=total,
                           pending=pending,
                           resolved=resolved)

@app.route("/admin_view_complaints")
def admin_view_complaints():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor = db.cursor(buffered=True)

    query = """
    SELECT 
    complaints.id,
    users.name,
    users.roll_no,
    users.email,
    complaints.category,
    complaints.subject,
    complaints.description,
    complaints.status,
    complaints.date
    FROM complaints
    JOIN users ON complaints.user_email = users.email
    """
    cursor.execute(query)
    complaints = cursor.fetchall()

    return render_template("admin_dashboard.html", complaints=complaints)

@app.route("/resolve/<int:id>")
def resolve(id):

    cursor = db.cursor()

    query = "UPDATE complaints SET status='Resolved' WHERE id=%s"
    cursor.execute(query,(id,))

    db.commit()

    return redirect("/admin_dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    error = None

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:

            session["admin"] = email
            return redirect("/admin_dashboard")

        else:
            error = "Invalid Admin Credentials"

    return render_template("admin_login.html", error=error)

@app.route("/admin_logout")
def admin_logout():

    session.pop("admin", None)
    return redirect("/admin_login")

@app.route("/reply/<int:id>", methods=["GET","POST"])
def reply(id):

    cursor = db.cursor()

    if request.method == "POST":

        reply = request.form["reply"]

        query = "UPDATE complaints SET status='Resolved', admin_reply=%s WHERE id=%s"

        cursor.execute(query,(reply,id))

        db.commit()

        return redirect("/admin_dashboard")

    return render_template("reply_complaint.html")


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form["name"]
        user_email = request.form["email"]
        message = request.form["message"]

        sender_email = "quickresolve1@gmail.com"
        app_password = "dyhnegcygqgiceha"

        receiver_email = "quickresolve1@gmail.com"

        subject = "New Contact Message"

        body = f"""
Name: {name}

User Email: {user_email}

Message:
{message}
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, app_password)

            server.sendmail(
                sender_email,
                receiver_email,
                msg.as_string()
            )

            server.quit()

            flash("Message sent successfully!")
            return redirect("/contact")

        except Exception as e:
            print("Contact email error:", e)
            flash("Failed to send message")
            return redirect("/contact")

    return render_template("contact.html")
@app.route('/delete/<int:id>')
def delete_complaint(id):

    cursor = db.cursor()

    query = "DELETE FROM complaints WHERE id=%s"
    cursor.execute(query,(id,))

    db.commit()
    return redirect("/view_complaints")

@app.route('/admin_delete/<int:id>')
def delete_admin_complaint(id):

    cursor = db.cursor()

    query = "DELETE FROM complaints WHERE id=%s"
    cursor.execute(query,(id,))

    db.commit()

    return redirect("/admin_dashboard")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

