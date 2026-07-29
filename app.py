from flask import Flask
from extensions import login_manager, ckeditor, bootstrap, gravatar
from dbhandler import init_app as init_db, get_user_by_id, User
from authhandler import FLASK_KEY, DB_URI
from blueprints.auth import auth_bp
from blueprints.posts import posts_bp
from blueprints.main_bp import main_bp


def create_app() -> Flask:
    """Application Factory pattern for Career Post Flask app."""
    app = Flask(__name__)
    app.secret_key = FLASK_KEY

    ckeditor.init_app(app)  # type: ignore[untyped-function]
    bootstrap.init_app(app)  # type: ignore[untyped-function]
    login_manager.init_app(app)  # type: ignore[untyped-function]
    gravatar.init_app(app)  # type: ignore[untyped-function]

    init_db(app, str(DB_URI))

    @login_manager.user_loader  # type: ignore[untyped-decorator]
    def load_user(user_id: str) -> User | None:
        """Load a user given their ID for Flask-Login."""
        return get_user_by_id(user_id)

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(main_bp)

    return app
