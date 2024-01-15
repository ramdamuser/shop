from flask import Flask, render_template, redirect, url_for
app = Flask(__name__)

@app.route("/products", methods=["GET", "POST"])
def products():
    return render_template("index.html")