import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_images import Images
from config import Config
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "login"
mail = Mail(app)
bootstrap = Bootstrap(app)
photos = UploadSet("photos", IMAGES)
images = Images(app)
configure_uploads(app, photos)
patch_request_class(app)  # set maximum file size, default is 16MB


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


if not app.debug:
    app_name = app.config["APPNAME"]
    if app.config["MAIL_SERVER"]:
        auth = None
        if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
            auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        secure = None
        if app.config["MAIL_USE_TLS"]:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
            fromaddr="no-reply@" + app.config["MAIL_SERVER"],
            toaddrs=app.config["ADMINS"],
            subject=f"{app_name} Failure",
            credentials=auth,
            secure=secure,
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists("logs"):
        os.mkdir("logs")
    file_handler = RotatingFileHandler(
        "logs/image-to-table.log", maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info(f"{app_name} startup")

from app import routes, models, errors
