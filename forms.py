from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, SubmitField, IntegerField, URLField
from wtforms.validators import DataRequired

class RegisterForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign me up!")

# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let me in!", validators=[DataRequired()])

class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired()])
    cost = IntegerField("Product cost(in AUD)", validators=[DataRequired()])
    img_url = URLField("Image URL", validators=[DataRequired()])
    submit = SubmitField("Add Product", validators=[DataRequired()])