from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import (
    LoginForm,
    RegistrationForm,
    EditProfileForm,
    ResetPasswordRequestForm,
    ChangePasswordForm,
    ResetPasswordForm,
    PhotoForm,
    ColumnForm,
    ColumnAgainForm,
)
from app.models import User, Image
from app.email import send_password_reset_email
from werkzeug.utils import secure_filename
from flask_uploads import UploadSet, IMAGES
from aws_helpers import (
    put_image_in_bucket,
    delete_all_files_for_image,
    put_excel_file_in_bucket,
    delete_remote_excel,
    put_csv_file_in_bucket,
    filename_helper,
)
import uuid
from threading import Thread
import pandas as pd
from api import analyze
import base64
import requests
import io
from image_crop import thumbnail


photos = UploadSet("photos", IMAGES)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_image(image_contents, full_filename):
    unique_id = uuid.uuid4().hex
    filename, file_ending = filename_helper(full_filename)
    Thread(
        target=put_image_in_bucket,
        args=(unique_id, image_contents, file_ending, filename),
    ).start()
    thumbnail_image_contents = thumbnail(image_contents, N=200)
    thumbnail_filename = f"{filename}_thumbnail"
    put_image_in_bucket(
        unique_id, thumbnail_image_contents, file_ending, thumbnail_filename
    )
    Thread(
        target=put_image_in_bucket,
        args=(unique_id, image_contents, file_ending, filename),
    ).start()
    image = Image(uuid=unique_id, user=current_user, filename=full_filename)
    db.session.add(image)
    db.session.commit()


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PhotoForm()
    if form.validate_on_submit():
        f = form.photo.data
        full_filename = secure_filename(f.filename)
        image_contents = f.read()
        upload_image(image_contents, full_filename)
        flash("Your image was uploaded!")
    images = list(reversed(Image.query.filter_by(user=current_user).all()))
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
        username = form.username.data
        user = User(username=username, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(
            f"Welcome, {username}! You're successfully registered and may now log in."
        )
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
        flash("Check your email for the instructions on how to reset your password.")
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
    print(app.config["APPNAME"])
    return render_template("reset_password.html", form=form)


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
    filename = image.filename
    Thread(target=delete_all_files_for_image, args=(unique_id, filename)).start()
    return redirect(url_for("index"))


@app.route("/delete_table/<unique_id>")
@login_required
def delete_table(unique_id):
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    image.tabular = None
    filename = image.filename
    # Thread(target=delete_remote_excel, args=(unique_id, filename)).start()
    delete_remote_excel(unique_id, filename)
    db.session.commit()
    flash("Table deleted.")
    return redirect(url_for("image", unique_id=unique_id))


@app.route("/extract_from_image/<unique_id>/<int:number_of_columns>")
@login_required
def extract_from_image(unique_id, number_of_columns, language):
    if number_of_columns < 1:
        flash("Number of columns must be a positive integer.")
        return redirect(url_for("index"))
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    # Fetch image from AWS S3:
    image_response = requests.get(image.image_url())
    if not image_response.status_code == 200:
        if image_response.status_code == 403:
            flash(
                "Image could not be retrieved, perhaps it had not finished uploading. Please try again."
            )
        else:
            flash("Something went wrong with getting the image from the internet.")
        return redirect(url_for("index"))
    image_content = image_response.content
    base64_encoded_image = base64.b64encode(image_content)
    image_json = {"base64_image": base64_encoded_image, "language": language}
    cleaned_filename = image.filename
    df_json = analyze(image_json=image_json, number_of_columns=number_of_columns)["df"]
    df = pd.read_json(df_json, orient="split")
    df.index = pd.RangeIndex(start=1, stop=(len(df.index) + 1))
    df.columns = pd.RangeIndex(start=1, stop=(len(df.columns) + 1))
    with io.BytesIO() as output:
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, header=None, index=None)
        writer.save()
        excel_binary_data = output.getvalue()
    filename = image.filename.rsplit(".")[0]
    Thread(
        target=put_excel_file_in_bucket, args=(unique_id, excel_binary_data, filename)
    ).start()
    with io.StringIO() as output:
        df.to_csv(output, header=None, index=None)
        contents = output.getvalue()
        csv_binary_data = str.encode(contents)
    Thread(
        target=put_csv_file_in_bucket, args=(unique_id, csv_binary_data, filename)
    ).start()
    image.tabular = df_json
    db.session.add(image)
    db.session.commit()
    flash("Table extracted!")
    return redirect(url_for("image", unique_id=unique_id))


@app.route("/image/<unique_id>", methods=["GET", "POST"])
@login_required
def image(unique_id):
    image = (
        Image.query.filter_by(uuid=unique_id)
        .filter_by(user=current_user)
        .first_or_404()
    )
    form = ColumnForm()
    form_again = ColumnAgainForm()
    if form.validate_on_submit():
        number_of_columns = form.columns.data
        language = form.language.data
        return extract_from_image(unique_id, number_of_columns, language=language)
    if form_again.validate_on_submit():
        number_of_columns = form_again.columns.data
        language = form_again.language.data
        return extract_from_image(unique_id, number_of_columns, anguage=language)
    if image.tabular:
        df_json = image.tabular
        df = pd.read_json(df_json, orient="split")
        df.index = pd.RangeIndex(start=1, stop=(len(df.index) + 1))
        df.columns = pd.RangeIndex(start=1, stop=(len(df.columns) + 1))
        rows = df.values.tolist()
    else:
        rows = None
    return render_template(
        "image.html", image=image, form=form, rows=rows, form_again=form_again
    )


@app.route("/delete_all_images/")
@login_required
def delete_all_images():
    images = list(reversed(Image.query.filter_by(user=current_user).all()))
    for image in images:
        Thread(target=delete_all_files_for_image, args=(image.uuid,)).start()
        db.session.delete(image)
        db.session.commit()
    if len(images) > 0:
        flash("All images were deleted.")
    return redirect(url_for("index"))


@app.route("/add_example_image/")
@login_required
def add_example_image():
    example_image_url = "http://vegardstikbakke.com/assets/img/example.png"
    example_filename = "example.png"
    image_response = requests.get(example_image_url)
    if not image_response.status_code == 200:
        flash("The example image could not be retrieved.")
        return redirect(url_for("index"))
    image_contents = image_response.content
    upload_image(image_contents, example_filename)
    flash("Example image was added.")
    return redirect(url_for("index"))
