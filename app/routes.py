from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import (
    LoginForm,
    RegistrationForm,
    EditProfileForm,
    ResetPasswordRequestForm,
    ResetPasswordForm,
    PhotoForm,
)
from app.models import User, Image
from app.email import send_password_reset_email
from werkzeug.utils import secure_filename
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from aws_helpers import put_image_in_bucket, get_url, delete_remote_image
import uuid
from threading import Thread
import pandas as pd
from api import analyze
import base64
import requests

photos = UploadSet("photos", IMAGES)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PhotoForm()
    if form.validate_on_submit():
        f = form.photo.data
        filename = secure_filename(f.filename)
        image_contents = f.read()
        unique_id = uuid.uuid4().hex
        Thread(target=put_image_in_bucket, args=(unique_id, image_contents)).start()
        remote_url = get_url(unique_id)
        image = Image(uuid=unique_id, user=current_user, filename=filename)
        db.session.add(image)
        db.session.commit()
        flash("Your image is uploaded!")
    images = Image.query.filter_by(user=current_user).all()
    return render_template("index.html", form=form, title="Home", images=images)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash("Check your email for the instructions to reset your password")
        return redirect(url_for("login"))
    return render_template(
        "reset_password_request.html", title="Reset Password", form=form
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)


@app.route("/user/<username>")
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    images = Image.query.filter_by(user=user).all()
    return render_template("user.html", user=user, images=images)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title="Edit Profile", form=form)


@app.route("/delete_image/<unique_id>")
@login_required
def delete_image(unique_id):
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    db.session.delete(image)
    db.session.commit()
    flash("Image deleted.")
    Thread(target=delete_remote_image, args=(unique_id,)).start()
    return redirect(url_for("index"))


@app.route("/extract_from_image/<unique_id>/<number_of_columns>")
@login_required
def extract_from_image(unique_id, number_of_columns):
    try:
        number_of_columns = int(number_of_columns)
    except ValueError:
        flash("Number of columns must be a positive integer.")
        return redirect(url_for("index"))
    if number_of_columns < 1:
        flash("Number of columns must be a positive integer.")
        return redirect(url_for("index"))
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    image_response = requests.get(image.url())
    if not image_response.status_code == 200:
        flash("Something went wrong with getting the image from the internet.")
        return redirect(url_for("index"))
    image_content = image_response.content
    base64_encoded_image = base64.b64encode(image_content)
    image_json = {"base64_image": base64_encoded_image}
    cleaned_filename = image.filename
    df_json = analyze(
        image_json=image_json,
        number_of_columns=number_of_columns,
        show=False,
        filepath=cleaned_filename,
    )
    image.tabular = df_json
    db.session.add(image)
    db.session.commit()
    flash("Table extracted.")
    return redirect(url_for("index"))


@app.route("/view_table/<unique_id>")
@login_required
def view_table(unique_id):
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    if not image.tabular:
        flash("Image doesn't have table data extracted.")
        return redirect(url_for("index"))
    df_json = image.tabular
    df = pd.read_json(df_json, orient="split")
    df.index = pd.RangeIndex(start=1, stop=(len(df.index) + 1))
    df.columns = pd.RangeIndex(start=1, stop=(len(df.columns) + 1))
    return render_template("table.html", table_html=df.to_html())
