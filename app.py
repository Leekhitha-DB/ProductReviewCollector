from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json, os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "products": [], "reviews": []}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------- AUTH ----------
@app.route("/", methods=["GET", "POST"])
def login():
    data = load_data()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Admin login
        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin")

        # User login
        for user in data["users"]:
            if user["username"] == username and check_password_hash(user["password"], password):
                session["user"] = username
                return redirect("/home")

        flash("Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    data = load_data()

    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        data["users"].append({
            "username": username,
            "password": password
        })

        save_data(data)
        return redirect("/")

    return render_template("register.html")

# ---------- USER ----------
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    data = load_data()
    return render_template("index.html", products=data["products"])

@app.route("/review/<int:pid>", methods=["POST"])
def add_review(pid):
    data = load_data()

    review = {
        "id": len(data["reviews"]) + 1,
        "product_id": pid,
        "user": session.get("user"),
        "rating": int(request.form["rating"]),
        "text": request.form["text"],
        "approved": False
    }

    data["reviews"].append(review)
    save_data(data)
    return redirect("/home")

@app.route("/product/<int:pid>")
def product(pid):
    data = load_data()
    product = next(p for p in data["products"] if p["id"] == pid)

    reviews = [r for r in data["reviews"] if r["product_id"] == pid and r["approved"]]

    return render_template("product.html", product=product, reviews=reviews)

# ---------- ADMIN ----------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/")

    data = load_data()
    pending = [r for r in data["reviews"] if not r["approved"]]

    return render_template("admin.html",
                           users=len(data["users"]),
                           products=data["products"],
                           pending=pending)

@app.route("/add_product", methods=["POST"])
def add_product():
    data = load_data()

    data["products"].append({
        "id": len(data["products"]) + 1,
        "name": request.form["name"]
    })

    save_data(data)
    return redirect("/admin")

@app.route("/approve/<int:rid>")
def approve(rid):
    data = load_data()
    for r in data["reviews"]:
        if r["id"] == rid:
            r["approved"] = True
    save_data(data)
    return redirect("/admin")

@app.route("/delete/<int:rid>")
def delete(rid):
    data = load_data()
    data["reviews"] = [r for r in data["reviews"] if r["id"] != rid]
    save_data(data)
    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)