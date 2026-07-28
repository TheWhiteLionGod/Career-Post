from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean
from flask_login import UserMixin  # type: ignore[import-untyped]


class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models."""
    pass


db = SQLAlchemy(model_class=Base)


def init_app(app: Flask, db_uri: str) -> None:
    """Initialize the Flask app with the database configuration.

    This function sets the SQLALCHEMY_DATABASE_URI from the ``db_uri``
    parameter, registers the ``db`` instance with the Flask app,
    and creates all tables.
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    db.init_app(app)
    with app.app_context():
        db.create_all()


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class Post(db.Model):  # type: ignore[name-defined, misc]
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str | None] = mapped_column(String, nullable=True)

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author: Mapped["User"] = relationship("User", back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="post")


class User(db.Model, UserMixin):  # type: ignore[name-defined, misc]
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    about_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="Hello, it's nice to meet you!"
    )
    admin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    premium: Mapped[bool] = mapped_column(Boolean, nullable=False)
    terminate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")


class Comment(db.Model):  # type: ignore[name-defined, misc]
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author: Mapped["User"] = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("posts.id"))
    post: Mapped["Post"] = relationship("Post", back_populates="comments")


# ---------------------------------------------------------------------------
# High-Level Database Wrapper Functions
# ---------------------------------------------------------------------------

def get_user_by_id(user_id: int | str) -> User | None:
    return db.get_or_404(User, user_id)


def get_user_by_email(email: str) -> User | None:
    return db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar()


def create_user_account(
    name: str,
    email: str,
    password: str,
    premium: bool = False,
    admin: bool = False
) -> User:
    new_user = User(name=name, email=email, password=password, admin=admin, premium=premium)  # type: ignore
    db.session.add(new_user)
    db.session.commit()
    return new_user


def update_user_about(user: User, about_text: str) -> None:
    user.about_text = about_text
    db.session.commit()


def mark_user_for_termination(email: str) -> None:
    user = get_user_by_email(email)
    if user:
        user.terminate = True
        db.session.commit()


def terminate_user_data(user: User) -> None:
    posts = db.session.execute(
        db.select(Post).where(Post.author_id == user.id)
    ).scalars().all()
    comments = db.session.execute(
        db.select(Comment).where(Comment.author_id == user.id)
    ).scalars().all()

    for post in posts:
        for comment in post.comments:
            db.session.delete(comment)
        db.session.delete(post)

    for comment in comments:
        db.session.delete(comment)

    db.session.delete(user)
    db.session.commit()


def set_user_admin(email: str, is_admin: bool) -> None:
    user = get_user_by_email(email)
    if user:
        user.admin = is_admin
        db.session.commit()


def set_user_premium(email: str, is_premium: bool) -> None:
    user = get_user_by_email(email)
    if user:
        user.premium = is_premium
        db.session.commit()


def get_all_posts() -> list[Post]:
    return list(db.session.execute(
        db.select(Post).order_by(Post.id)
    ).scalars().all())


def get_post_by_id(post_id: int | str) -> Post:
    return db.get_or_404(Post, post_id)


def get_post_by_title(title: str) -> Post | None:
    return db.session.execute(
        db.select(Post).where(Post.title == title)
    ).scalar()


def get_posts_by_author(author_id: int) -> list[Post]:
    return list(db.session.execute(
        db.select(Post).where(Post.author_id == author_id)
    ).scalars().all())


def add_new_post(
    title: str,
    subtitle: str,
    text: str,
    img_url: str | None,
    author: User,
    date_str: str
) -> Post:
    new_post = Post(title=title, subtitle=subtitle, text=text, img_url=img_url, author=author, date=date_str)  # type: ignore
    db.session.add(new_post)
    db.session.commit()
    return new_post


def update_post_details(
    post: Post,
    title: str,
    subtitle: str,
    img_url: str | None,
    text: str
) -> None:
    post.title = title
    post.subtitle = subtitle
    post.img_url = img_url
    post.text = text
    db.session.commit()


def delete_post_and_comments(post: Post) -> None:
    for comment in post.comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()


def get_comment_by_id(comment_id: int | str) -> Comment:
    return db.get_or_404(Comment, comment_id)


def add_new_comment(text: str, author: User, post: Post) -> Comment:
    new_comment = Comment(text=text, author=author, post=post)  # type: ignore
    db.session.add(new_comment)
    db.session.commit()
    return new_comment


def delete_single_comment(comment: Comment) -> None:
    db.session.delete(comment)
    db.session.commit()


def search_posts(query: str) -> list[Post]:
    return list(db.session.execute(
        db.select(Post).where(Post.title.contains(query))
    ).scalars().all())
