from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123" 

app = Flask(__name__)
app.secret_key = "1623"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1623",
    database="students_complaints")

cursor = db.cursor()

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


# Register user
@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    phone = request.form["phone"]

    query = "INSERT INTO users (name,email,password,phone) VALUES (%s,%s,%s,%s)"
    values = (name,email,password,phone)

    cursor.execute(query, values)
    db.commit()

    return redirect("/")

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

    cursor.execute("SELECT * FROM complaints")
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

@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)

