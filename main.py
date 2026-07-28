from __future__ import annotations
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    request,
    session,
    Response,
)
from flask_bootstrap import Bootstrap5  # type: ignore[import-untyped]
from flask_login import login_user, LoginManager, current_user, logout_user  # type: ignore[import-untyped]
from flask_wtf import FlaskForm  # type: ignore[import-untyped]
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email  # type: ignore[import-untyped]
from flask_ckeditor import CKEditor, CKEditorField  # type: ignore[import-untyped]
from flask_gravatar import Gravatar  # type: ignore[import-untyped]
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]
from sendgrid.helpers.mail import Mail  # type: ignore[import-untyped]
from werkzeug.wrappers.response import Response as WerkzeugResponse
from typing import Any, Callable, cast
import os

from dbhandler import (
    User,
    init_app,
    get_user_by_id,
    get_user_by_email,
    create_user_account,
    update_user_about,
    mark_user_for_termination,
    terminate_user_data,
    set_user_admin,
    set_user_premium,
    get_all_posts,
    get_post_by_id,
    get_post_by_title,
    get_posts_by_author,
    add_new_post,
    update_post_details,
    delete_post_and_comments,
    get_comment_by_id,
    add_new_comment,
    delete_single_comment,
    search_posts,
)

type RouteResponse = tuple[Response | WerkzeugResponse | str, int]
cast(User, current_user)

EMAIL: str | None = os.environ.get('EMAIL')
assert isinstance(EMAIL, str), "EMAIL environment variable is not set"

API: str | None = os.environ.get('SENDGRID')
assert isinstance(API, str), "SENDGRID environment variable is not set"

DB_URI: str | None = os.getenv('DB_URI')
assert isinstance(DB_URI, str), "DB_URI environment variable is not set"

FLASK_KEY: str | None = os.environ.get('FLASK_KEY')
assert isinstance(FLASK_KEY, str), "FLASK_KEY environment variable is not set"

app: Flask = Flask(__name__)
app.secret_key = FLASK_KEY

ckeditor: CKEditor = CKEditor(app)

bootstrap: Bootstrap5 = Bootstrap5(app)

login_manager: LoginManager = LoginManager()
login_manager.init_app(app)  # type: ignore[untyped-function]

init_app(app, DB_URI)


@login_manager.user_loader  # type: ignore[untyped-decorator]
def load_user(user_id: str) -> User | None:
    """Load a user given their ID for Flask-Login."""
    return get_user_by_id(user_id)


gravatar: Gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None)

year: int = datetime.now().year

dark_mode: bool = True


class RegisterForm(FlaskForm):  # type: ignore[misc]
    """Register form for user creation"""
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
    """Login form for user authentication"""
    email: StringField = StringField(
        "Email", validators=[
            DataRequired(), Email()])
    password: PasswordField = PasswordField(
        "Password", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Sign In")


class CreatePostForm(FlaskForm):  # type: ignore[misc]
    """Post creation form"""
    title: StringField = StringField("Post Title", validators=[DataRequired()])
    subtitle: StringField = StringField(
        "Subtitle", validators=[DataRequired()])
    img_url: StringField = StringField("Image URL")
    body: CKEditorField = CKEditorField(
        "Post Text", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Submit Post")


class CreateAboutForm(FlaskForm):  # type: ignore[misc]
    """About creation form"""
    body: CKEditorField = CKEditorField(
        "About Text", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Save")


class ContactForm(FlaskForm):  # type: ignore[misc]
    """Contact form"""
    name: StringField = StringField("Name", validators=[DataRequired()])
    email: StringField = StringField("Email", validators=[DataRequired()])
    phone: StringField = StringField(
        "Phone Number", validators=[
            DataRequired()])
    message: TextAreaField = TextAreaField(
        "Message", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Send")


class CommentForm(FlaskForm):  # type: ignore[misc]
    """Comment form"""
    comment: CKEditorField = CKEditorField(
        "Comment", validators=[DataRequired()])
    submit: SubmitField = SubmitField("Send Comment")


def terminate() -> bool:
    """Teminates current user if they should be"""
    if not current_user.terminate:
        return False

    user: User | None = get_user_by_email(current_user.email)
    if user is None:
        return False

    logout_user()
    terminate_user_data(user)
    flash('Your Account has been Terminated.')
    return True


def admin_only[F: Callable[..., RouteResponse]](function: F) -> F:
    """Decorator to restrict access to admin users only."""
    @wraps(function)
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> RouteResponse:
        if current_user.email == EMAIL:
            set_user_admin(EMAIL, True)
            return function(*args, **kwargs)

        if not (current_user.is_authenticated and current_user.admin):
            return abort(403)

        if terminate():
            return redirect(url_for('register')), 302

        return function(*args, **kwargs)
    return wrapper  # type: ignore[return-value]


def logged_on[F: Callable[..., RouteResponse]](function: F) -> F:
    """Decorator to require a user be logged in."""
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> RouteResponse:
        if not current_user.is_authenticated:
            flash('You Need to Login First')
            return redirect(url_for('login')), 302

        if terminate():
            return redirect(url_for('register')), 302

        return function(*args, **kwargs)
    return wrapper  # type: ignore[return-value]


@app.route('/')
def homepage() -> RouteResponse:
    """Render the homepage with recent posts."""
    posts = get_all_posts()
    return (
        render_template(
            'index.html',
            posts=list(reversed(posts)),
            active0="active",
            dark_mode=dark_mode,
            count_target=6,
            year=year,
            title="Career Post",
            logged_in=current_user.is_authenticated,
            user=current_user,
        ),
        200,
    )


@app.route('/register', methods=['GET', 'POST'])
def register() -> RouteResponse:
    """Returns register page / form"""
    premium: bool = bool(request.args.get('premium'))
    form = RegisterForm()
    if not form.validate_on_submit():  # type: ignore[untyped-function]
        return render_template(
            "form.html", form=form, active3="active", year=year, dark_mode=dark_mode,
            title="Register", logged_in=current_user.is_authenticated, user=current_user
        ), 200

    email = form.email.data or ""
    user = get_user_by_email(email)

    if user:
        flash("The Email You Entered Already Exists")
        return redirect('login'), 302

    if form.password.data != form.reenter_pass.data:
        flash("The Passwords You Entered Do Not Match")
        return render_template(
            "form.html", form=form, active3="active", year=year, dark_mode=dark_mode,
            title="Register", logged_in=current_user.is_authenticated, user=current_user
        ), 200

    name = form.name.data or ""
    password = generate_password_hash(
        password=form.password.data or "",
        method='pbkdf2:sha256',
        salt_length=8
    )

    new_user = create_user_account(
        name=name,
        email=email,
        password=password,
        premium=premium,
        admin=False
    )

    login_user(new_user)
    return redirect(url_for('posts')), 302


@app.route('/login', methods=['GET', 'POST'])
def login() -> RouteResponse:
    """Returns login page / form"""
    form = LoginForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        email = form.email.data or ""
        user = get_user_by_email(email)

        if user and check_password_hash(
                pwhash=user.password,
                password=form.password.data or ""):
            login_user(user)
            return redirect(url_for('posts')), 302

        flash("The Email/Password You Entered Is Invalid")

    return render_template("form.html", form=form, active2="active", year=year, dark_mode=dark_mode,
                           title="Log In", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/logout')
def logout() -> RouteResponse:
    """Logs out user"""
    logout_user()
    return redirect(url_for('login')), 302


@app.route('/posts')
def posts() -> RouteResponse:
    """Returns posts page"""
    posts = get_all_posts()
    return render_template('posts.html', posts=list(reversed(posts)), active1="active", dark_mode=dark_mode, count_target=20,
                           year=year, title="Latest Posts", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/view-post/<id>', methods=['GET', 'POST'])
def view_post(id: str) -> RouteResponse:
    """Returns requested post"""
    post = get_post_by_id(id)
    if not post:
        return redirect(url_for('posts')), 302

    posts = get_posts_by_author(post.author_id)
    author = get_user_by_id(post.author_id)
    form = CommentForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        if terminate():
            return redirect(url_for('register')), 302

        if not current_user.is_authenticated:
            flash('You Need to Login to Comment on Posts')
            return redirect(url_for('login')), 302

        user = get_user_by_id(current_user.get_id())
        add_new_comment(
            text=form.comment.data,
            author=user,
            post=post,
        )

    return render_template('viewer.html', comments=list(reversed(post.comments)), post=post, form=form, dark_mode=dark_mode, edit_url=url_for('edit_post', email=post.author.email, id=id), id=id, posts=list(reversed(
        posts)), count_target=3, email=post.author.email, title=post.title, subtitle=post.subtitle, name=post.author.name, text=post.text, image=post.img_url, year=year, logged_in=current_user.is_authenticated, user=current_user, author=author), 200


@app.route('/create-post', methods=['GET', 'POST'])
@logged_on
def create_post() -> RouteResponse:
    """Post creation page / form"""
    if not current_user.admin and not current_user.premium:
        posts = get_posts_by_author(current_user.id)
        for post in posts:
            if post.date == date.today().strftime("%B %d, %Y"):
                return redirect(url_for('about', email=current_user.email,
                                message='You Can Not Make Any More Posts Today')), 302

    form = CreatePostForm()
    if form.validate_on_submit():  # type: ignore[untyped-function]
        title_val = (form.title.data or "").title()
        post = get_post_by_title(title_val)

        if post:
            flash('A Post with that Title Already Exists')
        elif len(form.title.data or "") > 250 or len(form.subtitle.data or "") > 250:
            flash('The Title/Subtitle of your Post is Too Long')
        else:
            add_new_post(
                title=title_val,
                subtitle=form.subtitle.data or "",
                text=form.body.data or "",
                img_url=form.img_url.data,
                author=current_user,
                date_str=date.today().strftime("%B %d, %Y")
            )
            return redirect(url_for("posts")), 302

    return render_template("form.html", form=form, year=year, dark_mode=dark_mode,
                           title="Create Post", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/edit-post/<email>/<id>', methods=['GET', 'POST'])
@logged_on
def edit_post(email: str, id: str) -> RouteResponse:
    """Edit post page / form"""
    if current_user.email != email:
        return abort(403)

    posts = get_posts_by_author(current_user.id)
    post = get_post_by_id(id)

    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.text
    )

    if form.validate_on_submit():  # type: ignore[untyped-function]
        update_post_details(
            post=post,
            title=form.title.data or "",
            subtitle=form.subtitle.data or "",
            img_url=form.img_url.data,
            text=form.body.data or ""
        )
        return redirect(url_for('view_post', id=id)), 302

    return render_template('editor.html', form=form, dark_mode=dark_mode, posts=list(reversed(posts)), count_target=3, email=current_user.email,
                           title=current_user.name, name=current_user.name, text=current_user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/delete/<email>/<id>')
@logged_on
def delete_post(email: str, id: str) -> RouteResponse:
    """Delete post page"""
    if current_user.email != email and not current_user.admin:
        return abort(403)

    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'delete_post', email=email, id=id))), 302

    post = get_post_by_id(id)
    if post:
        delete_post_and_comments(post)
    return redirect(url_for('about', email=email)), 302


@app.route('/<email>', methods=['GET', 'POST'])
@app.route('/<email>/<message>')
def about(email: str, message: str = '') -> RouteResponse:
    """About page"""
    user = get_user_by_email(email)
    if not user:
        return redirect(url_for('posts')), 302

    posts = get_posts_by_author(user.id)

    if current_user.is_authenticated:
        form = ContactForm(
            name=current_user.name,
            email=current_user.email
        )
    else:
        form = ContactForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        name = form.name.data
        from_email = form.email.data
        phone = form.phone.data
        mail = form.message.data

        from_user = get_user_by_email(from_email)
        if from_user:
            sendmail = Mail(
                from_email=EMAIL,
                to_emails=email,
                subject='Someone Using Career Post Has Tried to Contact You',
                html_content=f'Name: {name}<br><br>Email: {from_email}<br><br>Phone Number: {phone}<br><br>Message:<br>{mail}'
            )

            sg = SendGridAPIClient(API)
            sg.send(sendmail)  # type: ignore[untyped-function]
            message = 'Email Successfully Sent'
        else:
            flash("The Email You Entered Is Invalid")

    return render_template('viewer.html', form=form, dark_mode=dark_mode, message=message, edit_url=url_for('edit_about', email=user.email), posts=list(reversed(
        posts)), count_target=3, email=user.email, title=user.name, name=user.name, text=user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user, author=user), 200


@app.route('/edit-about/<email>', methods=['GET', 'POST'])
@logged_on
def edit_about(email: str) -> RouteResponse:
    """Edit about page / form"""
    if current_user.email != email:
        return abort(403)

    posts = get_posts_by_author(current_user.id)
    form = CreateAboutForm(body=current_user.about_text)

    if form.validate_on_submit():  # type: ignore[untyped-function]
        update_user_about(current_user, form.body.data)
        return redirect(url_for('about', email=email)), 302

    return render_template('editor.html', form=form, dark_mode=dark_mode, posts=list(reversed(posts)), count_target=3, email=current_user.email,
                           title=current_user.name, name=current_user.name, text=current_user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/delete/<email>')
@logged_on
def delete_account(email: str) -> RouteResponse:
    """Delete account page"""
    if current_user.email != email and not current_user.admin:
        return abort(403)

    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'delete_account', email=email))), 302

    mark_user_for_termination(email)

    return redirect(
        url_for(
            'about', message="Account Deletion Pending", email=email)), 302


@app.route('/delete-comment/<id>')
@logged_on
def delete_comment(id: str) -> RouteResponse:
    """Delete comment page"""
    comment = get_comment_by_id(id)
    is_authorized = (
        current_user.admin
        or current_user.id == comment.author_id
        or comment.post.author.email == current_user.email
    )
    if not is_authorized:
        return abort(403)

    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'delete_comment', id=id))), 302

    post = get_post_by_id(comment.post_id)
    delete_single_comment(comment)
    return redirect(url_for('view_post', id=post.id)), 302


@app.route('/confirm', methods=['GET', 'POST'])
@logged_on
def confirm() -> RouteResponse:
    """Confirmation page"""
    target = request.args.get('target') or url_for('posts')
    if request.method == 'GET':
        return render_template('confirm.html', dark_mode=dark_mode, year=year,
                               logged_in=current_user.is_authenticated, user=current_user, post='', target=target), 200

    if request.method == 'POST':
        if 'delete' in request.form and request.form['delete']:
            session['delete'] = True
            return redirect(target), 302
        return redirect(url_for('posts')), 302

    return abort(403)


@app.route('/search/')
def search() -> RouteResponse:
    """Search results"""
    query: str = (request.args.get('query') or '').title()
    results = search_posts(query)
    return render_template('posts.html', posts=list(results), dark_mode=dark_mode, count_target=20,
                           year=year, title=query, logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/theme/<make>')
def theme(make: str) -> RouteResponse:
    """Theme changer"""
    global dark_mode
    if make == 'True':
        dark_mode = True
    elif make == 'False':
        dark_mode = False
    return redirect(url_for('posts')), 302


@app.route('/make-admin/<email>')
@admin_only
def make_admin(email: str) -> RouteResponse:
    """Make admin"""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'make_admin', email=email))), 302

    set_user_admin(email, True)
    return redirect(url_for('about', email=email)), 302


@app.route('/make-premium/<email>')
@admin_only
def make_premium(email: str) -> RouteResponse:
    """Make premium"""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'make_premium', email=email))), 302

    set_user_premium(email, True)
    return redirect(url_for('about', email=email)), 302


@app.route('/remove-admin/<email>')
@admin_only
def remove_admin(email: str) -> RouteResponse:
    """Remove admin"""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'remove_admin', email=email))), 302

    set_user_admin(email, False)
    return redirect(url_for('about', email=email)), 302


@app.route('/remove-premium/<email>')
@admin_only
def remove_premium(email: str) -> RouteResponse:
    """Remove premium"""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'confirm', target=url_for(
                    'remove_premium', email=email))), 302

    set_user_premium(email, False)
    return redirect(url_for('about', email=email)), 302


if __name__ == '__main__':
    app.run(debug=True)
