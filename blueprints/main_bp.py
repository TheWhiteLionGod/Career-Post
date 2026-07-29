from __future__ import annotations
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    request,
    session,
)
from flask_login import cu  # type: ignore[import-untyped]
from sendgrid import SendGridAPIClient  # type: ignore[import-untyped]
from sendgrid.helpers.mail import Mail  # type: ignore[import-untyped]
from typing import cast

from authhandler import RouteResponse, EMAIL, API, logged_on
from dbhandler import (
    User,
    get_all_posts,
    get_user_by_email,
    get_posts_by_author,
    update_user_about,
    search_posts,
)
from forms import ContactForm, CreateAboutForm
import state

current_user = cast(User, cu)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def homepage() -> RouteResponse:
    """Render the homepage with recent posts."""
    all_posts = get_all_posts()
    return (
        render_template(
            'index.html',
            posts=list(reversed(all_posts)),
            active0="active",
            dark_mode=state.dark_mode,
            count_target=6,
            year=state.year,
            title="Career Post",
            logged_in=current_user.is_authenticated,
            user=current_user,
        ),
        200,
    )


@main_bp.route('/<email>', methods=['GET', 'POST'])
@main_bp.route('/<email>/<message>')
def about(email: str, message: str = '') -> RouteResponse:
    """About page."""
    user = get_user_by_email(email)
    if not user:
        return redirect(url_for('posts.posts')), 302

    user_posts = get_posts_by_author(user.id)

    if current_user.is_authenticated:
        form = ContactForm(
            name=current_user.name,
            email=current_user.email
        )
    else:
        form = ContactForm()

    if form.validate_on_submit():  # type: ignore[untyped-function]
        name = form.name.data
        from_email: str = form.email.data or ""
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

    return render_template(
        'viewer.html',
        form=form,
        dark_mode=state.dark_mode,
        message=message,
        edit_url=url_for('main.edit_about', email=user.email),
        posts=list(reversed(user_posts)),
        count_target=3,
        email=user.email,
        title=user.name,
        name=user.name,
        text=user.about_text,
        year=state.year,
        logged_in=current_user.is_authenticated,
        user=current_user,
        author=user
    ), 200


@main_bp.route('/edit-about/<email>', methods=['GET', 'POST'])
@logged_on
def edit_about(email: str) -> RouteResponse:
    """Edit about page / form."""
    if current_user.email != email:
        return abort(403)

    user_posts = get_posts_by_author(current_user.id)
    form = CreateAboutForm(body=current_user.about_text)

    if form.validate_on_submit() and (about := form.body.data) is not None:  # type: ignore[untyped-function]
        update_user_about(current_user, about)
        return redirect(url_for('main.about', email=email)), 302

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


@main_bp.route('/confirm', methods=['GET', 'POST'])
@logged_on
def confirm() -> RouteResponse:
    """Confirmation page."""
    target = request.args.get('target') or url_for('posts.posts')
    if request.method == 'GET':
        return render_template(
            'confirm.html',
            dark_mode=state.dark_mode,
            year=state.year,
            logged_in=current_user.is_authenticated,
            user=current_user,
            post='',
            target=target
        ), 200

    if request.method == 'POST':
        if 'delete' in request.form and request.form['delete']:
            session['delete'] = True
            return redirect(target), 302
        return redirect(url_for('posts.posts')), 302

    return abort(403)


@main_bp.route('/search/')
def search() -> RouteResponse:
    """Search results."""
    query: str = (request.args.get('query') or '').title()
    results = search_posts(query)
    return render_template(
        'posts.html',
        posts=list(results),
        dark_mode=state.dark_mode,
        count_target=20,
        year=state.year,
        title=query,
        logged_in=current_user.is_authenticated,
        user=current_user
    ), 200


@main_bp.route('/theme/<make>')
def theme(make: str) -> RouteResponse:
    """Theme changer."""
    if make == 'True':
        state.dark_mode = True
    elif make == 'False':
        state.dark_mode = False
    return redirect(url_for('posts.posts')), 302
