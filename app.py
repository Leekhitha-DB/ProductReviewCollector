from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json, os

app = Flask(__name__)
app.secret_key = 'secretkey'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------------------------
# JSON FILES
# -------------------------
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
PRODUCTS_FILE = os.path.join(BASE_DIR, 'products.json')
REVIEWS_FILE = os.path.join(BASE_DIR, 'reviews.json')

# -------------------------
# HELPERS
# -------------------------
def load_data(file):
    if not os.path.exists(file):
        return []
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_next_id(data):
    return max([item['id'] for item in data], default=0) + 1

# -------------------------
# DECORATORS
# -------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect('/dashboard')
        return f(*args, **kwargs)
    return wrapper

# -------------------------
# AUTH
# -------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_data(USERS_FILE)

        email = request.form['email']
        password = request.form['password']

        user = next((u for u in users if u['email'] == email), None)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']

            return redirect('/admin' if user['role'] == 'admin' else '/dashboard')

        flash("Invalid credentials")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_data(USERS_FILE)

        email = request.form['email']
        # Check if the admin already exists in the users.json file
        admin_user = next((u for u in users if u['role'] == 'admin'), None)
        if admin_user and email == admin_user['email']:
            flash("Admin account already exists. Please log in.")
            return redirect('/')

        # Default role assignment
        role = "user"

        new_user = {
            "id": get_next_id(users),
            "name": request.form['name'],
            "email": email,
            "password": generate_password_hash(request.form['password']),
            "role": role
        }

        users.append(new_user)
        save_data(USERS_FILE, users)

        flash("Account created")
        return redirect('/')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# -------------------------
# ADMIN
# -------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    users = load_data(USERS_FILE)
    products = load_data(PRODUCTS_FILE)
    reviews = load_data(REVIEWS_FILE)

    # Calculate the number of products and reviews per product
    product_data = []
    for product in products:
        product_reviews = [r for r in reviews if r['product_id'] == product['id']]
        product_data.append({
            "id": product['id'],
            "name": product['name'],
            "image": product['image'],
            "avg_rating": product.get('avg_rating', 0),
            "review_count": len(product_reviews),
            "reviews": product_reviews
        })

    # Include user details in reviews
    for product in product_data:
        for review in product['reviews']:
            user = next((u for u in users if u['id'] == review['user_id']), None)
            if user:
                review['user_name'] = user['name']

    return render_template('admin.html',
                           users=users,
                           reviews=reviews,
                           products=product_data,
                           total_users=len(users),
                           total_products=len(products),
                           total_reviews=len(reviews))


@app.route('/add_product', methods=['POST'])
@admin_required
def add_product():
    products = load_data(PRODUCTS_FILE)

    image = request.files['image']
    filename = image.filename
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_product = {
        "id": get_next_id(products),
        "name": request.form['name'],
        "description": request.form['description'],
        "image": filename,
        "created_by": session['user_id'],
        "avg_rating": 0,
        "review_count": 0
    }

    products.append(new_product)
    save_data(PRODUCTS_FILE, products)

    return redirect('/admin')


@app.route('/make_admin/<int:id>')
@admin_required
def make_admin(id):
    users = load_data(USERS_FILE)

    for u in users:
        if u['id'] == id:
            u['role'] = 'admin'

    save_data(USERS_FILE, users)
    return redirect('/admin')


@app.route('/delete_review/<int:id>')
@admin_required
def delete_review(id):
    reviews = load_data(REVIEWS_FILE)
    reviews = [r for r in reviews if r['id'] != id]

    save_data(REVIEWS_FILE, reviews)
    return redirect('/admin')

# -------------------------
# ADMIN REGISTRATION
# -------------------------
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        users = load_data(USERS_FILE)

        email = request.form['email']
        if any(u['email'] == email for u in users):
            flash("Email already exists")
            return redirect('/admin_register')

        new_admin = {
            "id": get_next_id(users),
            "name": request.form['name'],
            "email": email,
            "password": generate_password_hash(request.form['password']),
            "role": "admin"
        }

        users.append(new_admin)
        save_data(USERS_FILE, users)

        flash("Admin account created")
        return redirect('/')

    return render_template('admin_register.html')

# -------------------------
# USER
# -------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    products = load_data(PRODUCTS_FILE)
    return render_template('dashboard.html', products=products)


@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def product(id):
    products = load_data(PRODUCTS_FILE)
    reviews = load_data(REVIEWS_FILE)

    if request.method == 'POST':
        new_review = {
            "id": get_next_id(reviews),
            "product_id": id,
            "user_id": session['user_id'],
            "rating": int(request.form['rating']),
            "text": request.form['text']
        }

        reviews.append(new_review)

        # recalc rating
        product_reviews = [r for r in reviews if r['product_id'] == id]
        avg = sum(r['rating'] for r in product_reviews) / len(product_reviews)

        for p in products:
            if p['id'] == id:
                p['avg_rating'] = round(avg, 2)
                p['review_count'] = len(product_reviews)

        save_data(REVIEWS_FILE, reviews)
        save_data(PRODUCTS_FILE, products)

    product = next(p for p in products if p['id'] == id)
    product_reviews = [r for r in reviews if r['product_id'] == id]

    return render_template('product.html', product=product, reviews=product_reviews)


# -------------------------
# USER DETAILS
# -------------------------
@app.route('/user_details/<int:user_id>')
@admin_required
def user_details(user_id):
    users = load_data(USERS_FILE)
    products = load_data(PRODUCTS_FILE)
    reviews = load_data(REVIEWS_FILE)

    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        flash("User not found")
        return redirect('/admin')

    user_reviews = [
        {
            "product_name": next((p['name'] for p in products if p['id'] == r['product_id']), "Unknown"),
            "product_image": next((p['image'] for p in products if p['id'] == r['product_id']), ""),
            "review_text": r['text'],
            "rating": r['rating']
        }
        for r in reviews if r['user_id'] == user_id
    ]

    return render_template('user_details.html', user=user, reviews=user_reviews)

# -------------------------
# INIT FILES
# -------------------------
def init_files():
    for file in [USERS_FILE, PRODUCTS_FILE, REVIEWS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

# -------------------------
# RUN
# -------------------------
if __name__ == '__main__':
    init_files()

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)
