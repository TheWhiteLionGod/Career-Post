from flask_bootstrap import Bootstrap5  # type: ignore[import-untyped]
from flask_login import LoginManager  # type: ignore[import-untyped]
from flask_ckeditor import CKEditor  # type: ignore[import-untyped]
from flask_gravatar import Gravatar  # type: ignore[import-untyped]

login_manager: LoginManager = LoginManager()
ckeditor: CKEditor = CKEditor()
bootstrap: Bootstrap5 = Bootstrap5()
gravatar: Gravatar = Gravatar(
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)
