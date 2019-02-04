import os
from flask import Flask, flash, request, redirect, url_for, send_from_directory
from flask_table import Table, Col
from werkzeug.utils import secure_filename
from api import analyze

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = set(["txt", "pdf", "png", "jpg", "jpeg", "gif"])

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print(app.config["UPLOAD_FOLDER"])
            print(filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return redirect(url_for("uploaded_file", filename=filename))
    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    <a href="/analyze">View uploaded files</a>
    """


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/show/filename")
def show_file(filename):
    return f"""
    <!doctype html>
    <title>Upload new File</title>
    <h1>Showing image</h1>
    <img src='/uploads/{filename}'>
    <a href="/analyze/{filename}">Analyze image!</a> 
    """


@app.route("/analyze/")
def analyze_head():
    path = "uploads"
    list_of_files = []
    for filename in os.listdir(path):
        list_of_files.append(filename)
    print(list_of_files)
    items = "".join(
        [
            f'<p><h2>{filename}</h2><br /><img src="../uploads/{filename}"><br /><a href="{filename}"><h3>Analyze</h3></a></p>'
            for filename in list_of_files
        ]
    )
    return f"""
    <!doctype html>
    <title>Analyze a file</title>
    <h1><a href="../">Back to home.</a>
    <h1>Analyze a file</h1>
    {items}
    """


@app.route("/analyze/<filename>")
def analyze_file(filename):
    full_filename = f"/uploads/{filename}"
    number_of_columns = 2
    df = analyze(
        filepath=full_filename,
        number_of_columns=number_of_columns,
        show=False,
        from_flask=True,
    )
    return df.to_html()


@app.route("/analyze/<filename>/<number_of_columns>")
def analyze_file_with_number_of_columns(filename, number_of_columns):
    full_filename = f"/uploads/{filename}"
    try:
        number_of_columns = int(number_of_columns)
    except ValueError:
        return f"""
        <h2>Number of columns must be an integer</h2>
        """
    df = analyze(
        filepath=full_filename,
        number_of_columns=number_of_columns,
        show=False,
        from_flask=True,
    )
    return df.to_html()
