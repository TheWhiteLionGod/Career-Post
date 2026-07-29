from __future__ import annotations
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    request,
    session as sess
)
from flask_login import login_user, logout_user, current_user  # type: ignore[import-untyped]
from werkzeug.security import generate_password_hash, check_password_hash
from typing import cast, Any

from authhandler import (
    RouteResponse,
    admin_only,
    logged_on,
)
from dbhandler import (
    get_user_by_email,
    create_user_account,
    mark_user_for_termination,
    set_user_admin,
    set_user_premium,
)
from forms import RegisterForm, LoginForm
import state

session = cast(dict[str, Any], sess)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register() -> RouteResponse:
    """Returns register page / form."""
    premium: bool = bool(request.args.get('premium'))
    form = RegisterForm()
    if not form.validate_on_submit():  # type: ignore[untyped-function]
        return render_template(
            "form.html", form=form, active3="active", year=state.year, dark_mode=state.dark_mode,
            title="Register", logged_in=current_user.is_authenticated, user=current_user
        ), 200

    email = form.email.data or ""
    user = get_user_by_email(email)

    if user:
        flash("The Email You Entered Already Exists")
        return redirect(url_for('auth.login')), 302

    if form.password.data != form.reenter_pass.data:
        flash("The Passwords You Entered Do Not Match")
        return render_template(
            "form.html", form=form, active3="active", year=state.year, dark_mode=state.dark_mode,
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
    return redirect(url_for('posts.posts')), 302


@auth_bp.route('/login', methods=['GET', 'POST'])
def login() -> RouteResponse:
    """Returns login page / form."""
    form = LoginForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        email = form.email.data or ""
        user = get_user_by_email(email)

        if user and check_password_hash(
                pwhash=user.password,
                password=form.password.data or ""):
            login_user(user)
            return redirect(url_for('posts.posts')), 302

        flash("The Email/Password You Entered Is Invalid")

    return render_template("form.html", form=form, active2="active", year=state.year, dark_mode=state.dark_mode,
                           title="Log In", logged_in=current_user.is_authenticated, user=current_user), 200


@auth_bp.route('/logout')
def logout() -> RouteResponse:
    """Logs out user."""
    logout_user()
    return redirect(url_for('auth.login')), 302


@auth_bp.route('/delete/<email>')
@logged_on
def delete_account(email: str) -> RouteResponse:
    """Delete account page."""
    if current_user.email != email and not current_user.admin:
        return abort(403)

    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'auth.delete_account', email=email))), 302

    mark_user_for_termination(email)

    return redirect(
        url_for(
            'main.about', message="Account Deletion Pending", email=email)), 302


@auth_bp.route('/make-admin/<email>')
@admin_only
def make_admin(email: str) -> RouteResponse:
    """Make admin."""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'auth.make_admin', email=email))), 302

    set_user_admin(email, True)
    return redirect(url_for('main.about', email=email)), 302


@auth_bp.route('/make-premium/<email>')
@admin_only
def make_premium(email: str) -> RouteResponse:
    """Make premium."""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'auth.make_premium', email=email))), 302

    set_user_premium(email, True)
    return redirect(url_for('main.about', email=email)), 302


@auth_bp.route('/remove-admin/<email>')
@admin_only
def remove_admin(email: str) -> RouteResponse:
    """Remove admin."""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'auth.remove_admin', email=email))), 302

    set_user_admin(email, False)
    return redirect(url_for('main.about', email=email)), 302


@auth_bp.route('/remove-premium/<email>')
@admin_only
def remove_premium(email: str) -> RouteResponse:
    """Remove premium."""
    verified: bool = bool(session.get('delete'))
    if not verified:
        return redirect(
            url_for(
                'main.confirm', target=url_for(
                    'auth.remove_premium', email=email))), 302

    set_user_premium(email, False)
    return redirect(url_for('main.about', email=email)), 302
