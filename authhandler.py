from __future__ import annotations
import os
from functools import wraps
from typing import Any, Callable
from flask import redirect, url_for, flash, abort, Response
from flask_login import current_user, logout_user  # type: ignore[import-untyped]
from werkzeug.wrappers.response import Response as WerkzeugResponse

from dbhandler import (
    User,
    get_user_by_email,
    terminate_user_data,
    set_user_admin,
)

type RouteResponse = tuple[Response | WerkzeugResponse | str, int]

EMAIL: str | None = os.environ.get('EMAIL')
assert isinstance(EMAIL, str), "EMAIL environment variable is not set"

API: str | None = os.environ.get('SENDGRID')
assert isinstance(API, str), "SENDGRID environment variable is not set"

DB_URI: str | None = os.getenv('DB_URI')
assert isinstance(DB_URI, str), "DB_URI environment variable is not set"

FLASK_KEY: str | None = os.environ.get('FLASK_KEY')
assert isinstance(FLASK_KEY, str), "FLASK_KEY environment variable is not set"


def terminate() -> bool:
    """Terminates current user if they should be."""
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
            set_user_admin(str(EMAIL), is_admin=True)

        if terminate():
            return redirect(url_for('auth.register')), 302

        if not (current_user.is_authenticated and current_user.admin):
            return abort(403)

        return function(*args, **kwargs)
    return wrapper  # type: ignore[return-value]


def logged_on[F: Callable[..., RouteResponse]](function: F) -> F:
    """Decorator to require a user be logged in."""
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> RouteResponse:
        if not current_user.is_authenticated:
            flash('You Need to Login First')
            return redirect(url_for('auth.login')), 302

        if terminate():
            return redirect(url_for('auth.register')), 302

        return function(*args, **kwargs)
    return wrapper  # type: ignore[return-value]
