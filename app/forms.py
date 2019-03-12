from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    IntegerField,
)
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
from flask_wtf.file import FileField, FileRequired, FileAllowed
from app.models import User
from flask_uploads import UploadSet, IMAGES


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email address.")


class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Request Password Reset")


class ChangePasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat password", validators=[DataRequired(), EqualTo("password")]
    )
    new_password = PasswordField("New password", validators=[DataRequired()])
    new_password2 = PasswordField(
        "Repeat new password", validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField("Set new password")


class EditProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)])
    submit = SubmitField("Submit")

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError("Please use a different username.")


photos = UploadSet("photos", IMAGES)


class PhotoForm(FlaskForm):
    photo = FileField(
        validators=[
            FileAllowed(photos, u"Image only!"),
            FileRequired(u"File was empty!"),
        ]
    )
    submit = SubmitField(u"Upload")


class ColumnForm(FlaskForm):
    columns = IntegerField(
        label="How many columns are there in the table?", validators=[DataRequired()]
    )
    submit = SubmitField("Extract table from image")

    def validate_columns(self, columns):
        if columns.data < 1:
            raise ValidationError("The number of columns is a positive integer.")


class ColumnAgainForm(FlaskForm):
    columns = IntegerField(
        label="Try again with a new number of columns?", validators=[DataRequired()]
    )
    submit = SubmitField("Extract table from image")

    def validate_columns(self, columns):
        if columns.data < 1:
            raise ValidationError("The number of columns is a positive integer.")
