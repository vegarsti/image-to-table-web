import os
from flask import (
    Flask,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    render_template,
)
from flask_table import Table, Col
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
            # return redirect(url_for("uploaded_file", filename=filename))
            return analyze_head()
    return render_template("index.html")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/excel_files/<filename>")
def download_excel(filename):
    return send_from_directory(app.config["EXCEL_DIRECTORY"], filename)


@app.route("/csvs/<filename>")
def download_csv(filename):
    return send_from_directory(app.config["CSV_DIRECTORY"], filename)


@app.route("/analyze/")
def analyze_head():
    path = "uploads"
    list_of_files = []
    for filename in os.listdir(path):
        if filename.rsplit(".")[-1] in ALLOWED_EXTENSIONS:
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
    csv_filename = filename.rsplit(".")[0] + ".csv"
    excel_filename = filename.rsplit(".")[0] + ".xlsx"
    return render_template(
        "table.html",
        filename=filename,
        csv_filename=csv_filename,
        excel_filename=excel_filename,
        table_html=df.to_html(),
    )


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
    csv_filename = filename.rsplit(".")[0] + ".csv"
    excel_filename = filename.rsplit(".")[0] + ".xlsx"
    return render_template(
        "table.html",
        filename=filename,
        csv_filename=csv_filename,
        excel_filename=excel_filename,
        table_html=df.to_html(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
