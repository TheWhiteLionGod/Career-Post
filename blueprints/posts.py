from __future__ import annotations
from datetime import date
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    session as sess,
)
from flask_login import cu  # type: ignore[import-untyped]
from typing import cast, Any

from authhandler import RouteResponse, logged_on, terminate
from dbhandler import (
    User,
    get_all_posts,
    get_post_by_id,
    get_posts_by_author,
    get_user_by_id,
    add_new_comment,
    get_post_by_title,
    add_new_post,
    update_post_details,
    delete_post_and_comments,
    get_comment_by_id,
    delete_single_comment,
)
from forms import CommentForm, CreatePostForm
import state

current_user = cast(User, cu)
session = cast(dict[str, Any], sess)

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/posts')
def posts() -> RouteResponse:
    """Returns posts page."""
    posts_list = get_all_posts()
    return render_template(
        'posts.html',
        posts=list(reversed(posts_list)),
        active1="active",
        dark_mode=state.dark_mode,
        count_target=20,
        year=state.year,
        title="Latest Posts",
        logged_in=current_user.is_authenticated,
        user=current_user
    ), 200


@posts_bp.route('/view-post/<id>', methods=['GET', 'POST'])
def view_post(id: str) -> RouteResponse:
    """Returns requested post."""
    post = get_post_by_id(id)
    if not post:
        return redirect(url_for('posts.posts')), 302

    posts_list = get_posts_by_author(post.author_id)
    author = get_user_by_id(post.author_id)
    form = CommentForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        if terminate():
            return redirect(url_for('auth.register')), 302

        if not current_user.is_authenticated:
            flash('You Need to Login to Comment on Posts')
            return redirect(url_for('auth.login')), 302

        user = get_user_by_id(current_user.get_id())
        if user is None:
            return redirect(url_for('auth.login')), 302

        if (comment := form.comment.data) is not None:
            add_new_comment(
                text=comment,
                author=user,
                post=post,
            )

    return render_template(
        'viewer.html',
        comments=list(reversed(post.comments)),
        post=post,
        form=form,
        dark_mode=state.dark_mode,
        edit_url=url_for('posts.edit_post', email=post.author.email, id=id),
        id=id,
        posts=list(reversed(posts_list)),
        count_target=3,
        email=post.author.email,
        title=post.title,
        subtitle=post.subtitle,
        name=post.author.name,
        text=post.text,
        image=post.img_url,
        year=state.year,
        logged_in=current_user.is_authenticated,
        user=current_user,
        author=author
    ), 200


@posts_bp.route('/create-post', methods=['GET', 'POST'])
@logged_on
def create_post() -> RouteResponse:
    """Post creation page / form."""
    if not current_user.admin and not current_user.premium:
        user_posts = get_posts_by_author(current_user.id)
        for post in user_posts:
            if post.date == date.today().strftime("%B %d, %Y"):
                return redirect(url_for('main.about', email=current_user.email,
                                message='You Can Not Make Any More Posts Today')), 302

    form = CreatePostForm()
    if form.validate_on_submit():  # type: ignore[untyped-function]
        title_val = (form.title.data or "").title()
        existing_post = get_post_by_title(title_val)

        if existing_post:
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
            return redirect(url_for("posts.posts")), 302

    return render_template(
        "form.html",
        form=form,
        year=state.year,
        dark_mode=state.dark_mode,
        title="Create Post",
        logged_in=current_user.is_authenticated,
        user=current_user
    ), 200


@posts_bp.route('/edit-post/<email>/<id>', methods=['GET', 'POST'])
@logged_on
def edit_post(email: str, id: str) -> RouteResponse:
    """Edit post page / form."""
    if current_user.email != email:
        return abort(403)

    user_posts = get_posts_by_author(current_user.id)
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
        return redirect(url_for('posts.view_post', id=id)), 302

    return render_template(
        'editor.html',
        form=form,
        dark_mode=state.dark_mode,
        posts=list(reversed(user_posts)),
        count_target=3,
        email=current_user.email,
        title=current_user.name,
        name=current_user.name,
        text=current_user.about_text,
        year=state.year,
        logged_in=current_user.is_authenticated,
        user=current_user
    ), 200


@posts_bp.route('/delete/<email>/<id>')
@logged_on
def delete_post(email: str, id: str) -> RouteResponse:
    """Delete post page."""
    if current_user.email != email and not current_user.admin:
        return abort(403)

    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'posts.delete_post', email=email, id=id))), 302

    post = get_post_by_id(id)
    if post:
        delete_post_and_comments(post)
    return redirect(url_for('main.about', email=email)), 302


@posts_bp.route('/delete-comment/<id>')
@logged_on
def delete_comment(id: str) -> RouteResponse:
    """Delete comment page."""
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
                'main.confirm', target=url_for(
                    'posts.delete_comment', id=id))), 302

    post = get_post_by_id(comment.post_id)
    delete_single_comment(comment)
    return redirect(url_for('posts.view_post', id=post.id)), 302
