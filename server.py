import base64
import os

import pandas as pd
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from api import analyze

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["EXCEL_DIRECTORY"] = "excel_files"
app.config["CSV_DIRECTORY"] = "csvs"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # max allowed image size: 16 MB


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
        file_contents = file.read()
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            # return redirect(url_for("uploaded_file", filename=filename))
    path = "uploads"
    list_of_files = []
    for filename in os.listdir(path):
        if filename.rsplit(".")[-1] in ALLOWED_EXTENSIONS:
            list_of_files.append(filename)
    columns = list(range(1, 5))
    any_files = len(list_of_files) > 0
    return render_template(
        "index.html",
        filenames=list_of_files,
        columns_options=columns,
        any_files=any_files,
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/excel_files/<filename>")
def download_excel(filename):
    return send_from_directory(app.config["EXCEL_DIRECTORY"], filename)


@app.route("/csvs/<filename>")
def download_csv(filename):
    return send_from_directory(app.config["CSV_DIRECTORY"], filename)


@app.route("/download", methods=["POST"])
def download():
    if request.method == "POST":
        filetype = request.form.get("filetype")
        image_filename = request.form.get("filename")
        if filetype is not None:
            if filetype == "csv":
                csv_filename = image_filename.rsplit(".")[0] + ".csv"
                return redirect(url_for(".download_csv", filename=csv_filename))
            elif filetype == "excel":
                excel_filename = image_filename.rsplit(".")[0] + ".xlsx"
                return redirect(url_for(".download_excel", filename=excel_filename))
    else:
        redirect("/")


@app.route("/delete", methods=["POST"])
def delete_file():
    if request.method == "POST":
        image_filename = request.form.get("image_filename", "")
        csv_filename = image_filename.rsplit(".")[0] + ".csv"
        excel_filename = image_filename.rsplit(".")[0] + ".xlsx"
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        except FileNotFoundError:
            pass
        try:
            os.remove(os.path.join(app.config["CSV_DIRECTORY"], csv_filename))
        except FileNotFoundError:
            pass
        try:
            os.remove(os.path.join(app.config["EXCEL_DIRECTORY"], excel_filename))
        except FileNotFoundError:
            pass
    return redirect("/")


analyze_cache = {}


@app.route("/analyze/<filename>/<number_of_columns>")
def analyze_file_with_number_of_columns(filename, number_of_columns):
    full_filename = f"/uploads/{filename}"
    try:
        number_of_columns = int(number_of_columns)
    except ValueError:
        return f"""
        <h2>Number of columns must be an integer</h2>
        """
    df = analyze_cache.get((filename, number_of_columns))
    if df is None:
        cleaned_filename = full_filename[1:]
        try:
            with open(cleaned_filename, "rb") as file_descriptor:
                image_string = file_descriptor.read()
                base64_encoded_image = base64.b64encode(image_string)
        except FileNotFoundError:
            redirect("/", error="File not found!")
        image_json = {"base64_image": base64_encoded_image}
        df = analyze(
            image_json=image_json,
            number_of_columns=number_of_columns,
            show=False,
            filepath=cleaned_filename,
        )
        # df_json = ^
        # df = pd.read_json(df_json)
        analyze_cache[(filename, number_of_columns)] = df
    df.index = pd.RangeIndex(start=1, stop=(len(df.index) + 1))
    df.columns = pd.RangeIndex(start=1, stop=(len(df.columns) + 1))
    filetypes = ["csv", "excel"]
    return render_template(
        "table.html", filename=filename, filetypes=filetypes, table_html=df.to_html()
    )


@app.route("/analyze_post", methods=["POST"])
def analyze_post():
    assert request.method == "POST"
    form_options = {}
    for key in request.form:
        try:
            form_options[key] = int(request.form[key])
        except:
            form_options[key] = request.form[key]
    filename = form_options.get("filename")
    number_of_columns = form_options.get("columns")
    return analyze_file_with_number_of_columns(filename, number_of_columns)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
