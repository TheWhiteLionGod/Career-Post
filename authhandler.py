from typing import Sequence
from dbhandler import User, Post, Comment, SQLAlchemy
from flask_login import logout_user
from flask import flash

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