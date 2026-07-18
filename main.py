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
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean # type: ignore[import-untyped]
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_wtf import FlaskForm  # type: ignore[import-untyped]
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email # type: ignore[import-untyped]
from flask_ckeditor import CKEditor, CKEditorField
from flask_gravatar import Gravatar  # type: ignore[import-untyped]
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]
from sendgrid.helpers.mail import Mail  # type: ignore[import-untyped]
from werkzeug.wrappers.response import Response as WerkzeugResponse
from typing import Any, Callable
import os

type RouteResponse = tuple[Response | WerkzeugResponse | str, int]

if (EMAIL := os.environ.get('EMAIL')) is None:
    raise ValueError("EMAIL environment variable is not set")

if (API := os.environ.get('SENDGRID')) is None:
    raise ValueError("SENDGRID environment variable is not set")

app: Flask = Flask(__name__)
if (flask_key := os.environ.get('FLASK_KEY')) is None:
    raise ValueError("FLASK_KEY environment variable is not set")
app.secret_key = flask_key

ckeditor: CKEditor = CKEditor(app)

bootstrap: Bootstrap5 = Bootstrap5(app)

login_manager: LoginManager = LoginManager()
login_manager.init_app(app)

class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass

if (db_uri := os.environ.get('DB_URI')) is None:
    raise ValueError("DB_URI environment variable is not set")
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
db: SQLAlchemy = SQLAlchemy(model_class=Base)
db.init_app(app)


@login_manager.user_loader  # type: ignore[untyped-decorator]
def load_user(user_id: str) -> User | None:
    """Load a user given their ID for Flask-Login."""
    return db.get_or_404(User, user_id)


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


class Post(db.Model):  # type: ignore[name-defined, misc]
    """Post model representing blog posts."""
    __tablename__: str = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(
        String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str | None] = mapped_column(String, nullable=True)

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author: Mapped['User'] = relationship("User", back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="post")


class User(db.Model, UserMixin):  # type: ignore[name-defined, misc]
    """User model representing application users."""
    __tablename__: str = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(
        String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    about_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="Hello, it's nice to meet you!")

    admin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    premium: Mapped[bool] = mapped_column(Boolean, nullable=False)
    terminate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")


class Comment(db.Model):  # type: ignore[name-defined, misc]
    """Comment model representing comments on posts."""
    __tablename__: str = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    author_id: Mapped[int] = mapped_column(
        Integer, db.ForeignKey("users.id"), unique=False)
    author: Mapped["User"] = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(
        Integer, db.ForeignKey("posts.id"), unique=False)
    post: Mapped["Post"] = relationship("Post", back_populates="comments")


with app.app_context():
    db.create_all()


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
    if current_user.terminate:
        user: User | None = db.session.execute(
            db.select(User).where(
                User.email == current_user.email)).scalar()
        if user is not None:
            posts = db.session.execute(
                db.select(Post).where(
                    Post.author_id == user.id)).scalars().all()
            comments = db.session.execute(
                db.select(Comment).where(
                    Comment.author_id == user.id)).scalars().all()
            for post in posts:
                for comment in post.comments:
                    db.session.delete(comment)
                db.session.delete(post)

            for comment in comments:
                db.session.delete(comment)

            logout_user()
            db.session.delete(user)
            db.session.commit()

            flash('Your Account has been Terminated.')
            return True
    return False


def admin_only[F: Callable[..., RouteResponse]](function: F) -> F:
    """Decorator to restrict access to admin users only."""
    @wraps(function)
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> RouteResponse:
        if current_user.email != EMAIL:
            if current_user.is_authenticated and current_user.admin:
                if terminate():
                    return redirect(url_for('register')), 302
                return function(*args, **kwargs)
            return abort(403)
        else:
            user: User = db.get_or_404(User, 1)
            user.admin = True
            db.session.commit()
            return function(*args, **kwargs)
    return wrapper  # type: ignore[return-value]


def logged_on[F: Callable[..., RouteResponse]](function: F) -> F:
    """Decorator to require a user be logged in."""
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> RouteResponse:
        if current_user.is_authenticated:
            if terminate():
                return redirect(url_for('register')), 302
            return function(*args, **kwargs)
        else:
            flash('You Need to Login First')
            return redirect(url_for('login')), 302
    return wrapper  # type: ignore[return-value]


@app.route('/')
def homepage() -> RouteResponse:
    """Render the homepage with recent posts."""
    posts = db.session.execute(
        db.select(Post).order_by(
            Post.id)).scalars().all()
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
    if form.validate_on_submit():
        email = form.email.data or ""
        user = db.session.execute(
            db.select(User).where(
                User.email == email)).scalar()

        if not user:
            if form.password.data == form.reenter_pass.data:
                name = form.name.data or ""
                password = generate_password_hash(
                    password=form.password.data or "",
                    method='pbkdf2:sha256',
                    salt_length=8)

                if premium:
                    new_user = User(
                        email=email,
                        name=name,
                        password=password,
                        admin=False,
                        premium=True
                    )
                else:
                    new_user = User(
                        email=email,
                        name=name,
                        password=password,
                        admin=False,
                        premium=False
                    )

                db.session.add(new_user)
                db.session.commit()

                login_user(new_user)
                return redirect(url_for('posts')), 302
            flash("The Passwords You Entered Do Not Match")
        else:
            flash("The Email You Entered Already Exists")
            return redirect('login'), 302
    return render_template("form.html", form=form, active3="active", year=year, dark_mode=dark_mode,
                           title="Register", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/login', methods=['GET', 'POST'])
def login() -> RouteResponse:
    """Returns login page / form"""
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data or ""
        user = db.session.execute(
            db.select(User).where(
                User.email == email)).scalar()

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
    posts = db.session.execute(
        db.select(Post).order_by(
            Post.id)).scalars().all()
    return render_template('posts.html', posts=list(reversed(posts)), active1="active", dark_mode=dark_mode, count_target=20,
                           year=year, title="Latest Posts", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/view-post/<id>', methods=['GET', 'POST'])
def view_post(id: str) -> RouteResponse:
    """Returns requested post"""
    post = db.get_or_404(Post, id)

    if post:
        posts = db.session.execute(db.select(Post).where(
            Post.author_id == post.author_id)).scalars().all()
        author = db.get_or_404(User, post.author_id)
        form = CommentForm()

        if form.validate_on_submit():
            if terminate():
                return redirect(url_for('register')), 302

            if current_user.is_authenticated:
                user = db.get_or_404(User, current_user.get_id())

                new_comment = Comment(
                    text=form.comment.data,
                    author=user,
                    post=post,
                )

                db.session.add(new_comment)
                db.session.commit()
            else:
                flash('You Need to Login to Comment on Posts')
                return redirect(url_for('login')), 302
        return render_template('viewer.html', comments=list(reversed(post.comments)), post=post, form=form, dark_mode=dark_mode, edit_url=url_for('edit_post', email=post.author.email, id=id), id=id, posts=list(reversed(
            posts)), count_target=3, email=post.author.email, title=post.title, subtitle=post.subtitle, name=post.author.name, text=post.text, image=post.img_url, year=year, logged_in=current_user.is_authenticated, user=current_user, author=author), 200

    return redirect(url_for('posts')), 302


@app.route('/create-post', methods=['GET', 'POST'])
@logged_on
def create_post() -> RouteResponse:
    """Post creation page / form"""
    if not current_user.admin and not current_user.premium:
        posts = db.session.execute(db.select(Post).where(
            Post.author_id == current_user.id)).scalars().all()
        for post in posts:
            if post.date == date.today().strftime("%B %d, %Y"):
                return redirect(url_for('about', email=current_user.email,
                                message='You Can Not Make Any More Posts Today')), 302

    form = CreatePostForm()
    if form.validate_on_submit():
        title_val = (form.title.data or "").title()
        post = db.session.execute(
            db.select(Post).where(
                Post.title == title_val)).scalar()

        if post:
            flash('A Post with that Title Already Exists')
        else:
            if len(
                    form.title.data or "") <= 250 and len(
                    form.subtitle.data or "") <= 250:
                new_post = Post(
                    title=title_val,
                    subtitle=form.subtitle.data or "",
                    text=form.body.data or "",
                    img_url=form.img_url.data,
                    author=current_user,
                    date=date.today().strftime("%B %d, %Y")
                )

                db.session.add(new_post)
                db.session.commit()
                return redirect(url_for("posts")), 302
            else:
                flash('The Title/Subtitle of your Post is Too Long')

    return render_template("form.html", form=form, year=year, dark_mode=dark_mode,
                           title="Create Post", logged_in=current_user.is_authenticated, user=current_user), 200


@app.route('/edit-post/<email>/<id>', methods=['GET', 'POST'])
@logged_on
def edit_post(email: str, id: str) -> RouteResponse:
    """Edit post page / form"""
    if current_user.email == email:
        posts = db.session.execute(
            db.select(Post).where(
                Post.author_id == current_user.id)).scalars().all()
        post = db.get_or_404(Post, id)

        form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            body=post.text
        )

        if form.validate_on_submit():
            post.title = form.title.data or ""
            post.subtitle = form.subtitle.data or ""
            post.img_url = form.img_url.data
            post.text = form.body.data or ""

            db.session.commit()
            return redirect(url_for('view_post', id=id)), 302

        return render_template('editor.html', form=form, dark_mode=dark_mode, posts=list(reversed(posts)), count_target=3, email=current_user.email,
                               title=current_user.name, name=current_user.name, text=current_user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user), 200
    return abort(403)


@app.route('/delete/<email>/<id>')
@logged_on
def delete_post(email: str, id: str) -> RouteResponse:
    """Delete post page"""
    if current_user.email == email or current_user.admin:
        verified: bool = bool(session.get('delete'))
        if not verified:
            return redirect(
                url_for(
                    'confirm', target=url_for(
                        'delete_post', email=email, id=id))), 302

        post = db.get_or_404(Post, id)
        for comment in post.comments:
            db.session.delete(comment)

        db.session.delete(post)
        db.session.commit()
        return redirect(url_for('about', email=email)), 302

    return abort(403)


@app.route('/<email>', methods=['GET', 'POST'])
@app.route('/<email>/<message>')
def about(email: str, message: str = '') -> RouteResponse:
    """About page"""
    user = db.session.execute(
        db.select(User).where(
            User.email == email)).scalar()
    if user:
        posts = db.session.execute(
            db.select(Post).where(
                Post.author_id == user.id)).scalars().all()

        if current_user.is_authenticated:
            form = ContactForm(
                name=current_user.name,
                email=current_user.email
            )
        else:
            form = ContactForm()

        if form.validate_on_submit():
            name = form.name.data
            from_email = form.email.data
            phone = form.phone.data
            mail = form.message.data

            from_user = db.session.execute(
                db.select(User).where(
                    User.email == from_email)).scalar()
            if from_user:
                sendmail = Mail(
                    from_email=EMAIL,
                    to_emails=email,
                    subject='Someone Using Career Post Has Tried to Contact You',
                    html_content=f'Name: {name}<br><br>Email: {from_email}<br><br>Phone Number: {phone}<br><br>Message:<br>{mail}'
                )

                sg = SendGridAPIClient(API)
                sg.send(sendmail)
                message = 'Email Successfully Sent'
            else:
                flash("The Email You Entered Is Invalid")

        return render_template('viewer.html', form=form, dark_mode=dark_mode, message=message, edit_url=url_for('edit_about', email=user.email), posts=list(reversed(
            posts)), count_target=3, email=user.email, title=user.name, name=user.name, text=user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user, author=user), 200
    return redirect(url_for('posts')), 302


@app.route('/edit-about/<email>', methods=['GET', 'POST'])
@logged_on
def edit_about(email: str) -> RouteResponse:
    """Edit about page / form"""
    if current_user.email == email:
        posts = db.session.execute(
            db.select(Post).where(
                Post.author_id == current_user.id)).scalars().all()
        form = CreateAboutForm(body=current_user.about_text)

        if form.validate_on_submit():
            current_user.about_text = form.body.data
            db.session.commit()
            return redirect(url_for('about', email=email)), 302
        return render_template('editor.html', form=form, dark_mode=dark_mode, posts=list(reversed(posts)), count_target=3, email=current_user.email,
                               title=current_user.name, name=current_user.name, text=current_user.about_text, year=year, logged_in=current_user.is_authenticated, user=current_user), 200
    return abort(403)


@app.route('/delete/<email>')
@logged_on
def delete_account(email: str) -> RouteResponse:
    """Delete account page"""
    if current_user.email == email or current_user.admin:
        verified: bool = bool(session.get('delete'))
        if not verified:
            return redirect(
                url_for(
                    'confirm', target=url_for(
                        'delete_account', email=email))), 302

        user = db.session.execute(
            db.select(User).where(
                User.email == email)).scalar()
        user.terminate = True
        db.session.commit()

        return redirect(
            url_for(
                'about', message="Account Deletion Pending", email=email)), 302
    return abort(403)


@app.route('/delete-comment/<id>')
@logged_on
def delete_comment(id: str) -> RouteResponse:
    """Delete comment page"""
    comment = db.get_or_404(Comment, id)
    if current_user.admin or current_user.id == comment.author_id or comment.post.author.email == current_user.email:
        verified: bool = bool(session.get('delete'))
        if not verified:
            return redirect(
                url_for(
                    'confirm', target=url_for(
                        'delete_comment', id=id))), 302

        post = db.get_or_404(Post, comment.post_id)
        db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('view_post', id=post.id)), 302
    return abort(403)


@app.route('/confirm', methods=['GET', 'POST'])
@logged_on
def confirm() -> RouteResponse:
    """Confirmation page"""
    target = request.args.get('target') or url_for('posts')
    if request.method == 'GET':
        return render_template('confirm.html', dark_mode=dark_mode, year=year,
                               logged_in=current_user.is_authenticated, user=current_user, post='', target=target), 200
    elif request.method == 'POST':
        try:
            if request.form['delete']:
                session['delete'] = True
                return redirect(target), 302
        except KeyError:
            return redirect(url_for('posts')), 302
    return abort(403)


@app.route('/search/')
def search() -> RouteResponse:
    """Search results"""
    query: str = (request.args.get('query') or '').title()
    results = Post.query.filter(Post.title.contains(query)).all()
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

    user = db.session.execute(
        db.select(User).where(
            User.email == email)).scalar()
    user.admin = True
    db.session.commit()
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

    user = db.session.execute(
        db.select(User).where(
            User.email == email)).scalar()
    user.premium = True
    db.session.commit()
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

    user = db.session.execute(
        db.select(User).where(
            User.email == email)).scalar()
    user.admin = False
    db.session.commit()
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

    user = db.session.execute(
        db.select(User).where(
            User.email == email)).scalar()
    user.premium = False
    db.session.commit()
    return redirect(url_for('about', email=email)), 302


if __name__ == '__main__':
    app.run(debug=True)
