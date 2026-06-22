from typing import Sequence, Callable, Any
from dbhandler import User, Post, Comment, SQLAlchemy
from flask_login import logout_user, current_user
from flask import flash, redirect, abort, url_for
from functools import wraps
import os

EMAIL = os.environ.get('EMAIL')

# Terminating Account
def terminate(user: User, db: SQLAlchemy) -> bool:
    if not user.terminate:
        return False
    
    posts: Sequence[Post] = db.session.execute(db.select(Post).where(Post.author_id==user.id)).scalars().all()
    comments: Sequence[Comment] = db.session.execute(db.select(Comment).where(Comment.author_id==user.id)).scalars().all()
    
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

# Admin Only Decorator
def admin_only(db: SQLAlchemy) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    @wraps(admin_only)
    def outerWrapper(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
            if current_user.email == EMAIL:
                current_user.admin = True
                db.session.commit()
            
            if current_user.is_authenticated and current_user.admin:
                if terminate(current_user, db):
                    return redirect(url_for('register'))
                return function(*args, **kwargs)
            return abort(403)
        return wrapper
    return outerWrapper
