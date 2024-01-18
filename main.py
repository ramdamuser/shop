from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, ProductForm
from functools import wraps
import os, stripe
app = Flask(__name__)
Bootstrap(app)

app.config['SECRET_KEY'] = 'qwerty12'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)

db = SQLAlchemy(app)
# db.init_app(app)



@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

user_product = db.Table('user_product',
                    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                    db.Column('product_id', db.Integer, db.ForeignKey('products.id'))
                    )

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(255))
    name = db.Column(db.String(100))
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(100), unique=True)
    cost = db.Column(db.Integer)
    img_url = db.Column(db.Text(30000))
    cart_items = db.relationship('CartItem', backref='product', lazy=True)

class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    img_url = db.Column(db.Text(30000))

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

with app.app_context():
    db.create_all()

stripe.api_key = "sk_test_51OYdTuDjhT2uQWOrajbub0652t7C2vyMUO8rfwxfEaFwxpfAsJWUH23mx0OBtO1r0YTwSK1X1rCGkfE6VlsIPFIS00G9dg58Ox"

@app.route("/products")
def products():
    products = db.session.execute(db.select(Product)).scalars()
    return render_template("products.html", products=products)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=8)
        name = form.name.data
        new_user = User(email=email, password=password, name=name)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("products"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("products"))
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))
        flash("That email does not exist, please try again.")
    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("products"))

@app.route("/add_product", methods=["GET", "POST"])
@admin_only
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(name=form.name.data, cost=form.cost.data, img_url=form.img_url.data)
        db.session.add(new_product)
        db.session.commit()
        stripe_product = stripe.Product.create(name=form.name.data)
        stripe.Price.create(
            product=stripe_product.id,
            unit_amount=form.cost.data * 100,
            currency="aud"
        )
        return redirect(url_for("products"))
    return render_template("add_product.html", form=form)

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if current_user.is_authenticated:
        product_to_add = Product.query.get(product_id)
        if product_to_add:
            cart_item = CartItem.query.filter_by(user=current_user, product=product_to_add).first()

            if cart_item:
                # If the item is already in the cart, increment the quantity
                cart_item.quantity += 1
            else:
                # If the item is not in the cart, create a new cart item
                cart_item = CartItem(user=current_user, product=product_to_add, img_url=product_to_add.img_url)

            db.session.add(cart_item)
            db.session.commit()

            return redirect(url_for("products"))
        else:
            flash("Product not found.")
    else:
        flash("In order to add to cart, login first!")

    return redirect(url_for("login"))

@app.route("/create_checkout_session")
def create_checkout_session():
    cart_items = current_user.cart_items
    stripe_prices = stripe.Price.list()["data"]
    stripe_prices.reverse()
    print(stripe_prices)
    line_items = []
    for cart_item in cart_items:
        line_items.append({
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': stripe_prices[cart_item.id - 1]["id"],
                    'quantity': cart_item.quantity,
                })
    print(line_items)
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url="http://127.0.0.1:5000/success",
            cancel_url="http://127.0.0.1:5000/cancel"
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)

@app.route("/success")
def success():
    for cart_item in current_user.cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    return render_template("cancel.html")