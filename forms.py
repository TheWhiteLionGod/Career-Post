from flask_wtf import FlaskForm  # type: ignore[import-untyped]
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email  # type: ignore[import-untyped]
from flask_ckeditor import CKEditorField  # type: ignore[import-untyped]


class RegisterForm(FlaskForm):  # type: ignore[misc]
    """Register form for user creation."""
    name: StringField = StringField("Name", validators=[DataRequired()])
    email: StringField = StringField(
        "Email", validators=[
            DataRequired(), Email()])
    password: PasswordField = PasswordField(
        "Password", validators=[DataRequired()])
    reenter_pass: PasswordField = PasswordField(
        "Re Enter Password", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Sign Up")


class LoginForm(FlaskForm):  # type: ignore[misc]
    """Login form for user authentication."""
    email: StringField = StringField(
        "Email", validators=[
            DataRequired(), Email()])
    password: PasswordField = PasswordField(
        "Password", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Sign In")


class CreatePostForm(FlaskForm):  # type: ignore[misc]
    """Post creation form."""
    title: StringField = StringField("Post Title", validators=[DataRequired()])
    subtitle: StringField = StringField(
        "Subtitle", validators=[DataRequired()])
    img_url: StringField = StringField("Image URL")
    body: CKEditorField = CKEditorField(
        "Post Text", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Submit Post")


class CreateAboutForm(FlaskForm):  # type: ignore[misc]
    """About creation form."""
    body: CKEditorField = CKEditorField(
        "About Text", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Save")


class ContactForm(FlaskForm):  # type: ignore[misc]
    """Contact form."""
    name: StringField = StringField("Name", validators=[DataRequired()])
    email: StringField = StringField("Email", validators=[DataRequired()])
    phone: StringField = StringField(
        "Phone Number", validators=[
            DataRequired()])
    message: TextAreaField = TextAreaField(
        "Message", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Send")


class CommentForm(FlaskForm):  # type: ignore[misc]
    """Comment form."""
    comment: CKEditorField = CKEditorField(
        "Comment", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Send Comment")
