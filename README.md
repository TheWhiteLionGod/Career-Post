# Career Post

A full-stack blogging and professional networking platform built with **Flask**. Users can register, publish posts with rich-text formatting, maintain a personal "About Me" page, and contact each other directly — all backed by a tiered membership system (Free and Premium).

---

## Features

### For All Users
- Browse the post feed and search posts by title
- View any user's About Me page
- Light / Dark mode toggle (persisted per-session)

### Free Accounts
- 1 post per day
- Personal About Me page

### Premium (Pro / Donate) Accounts
- Unlimited posts
- Rich-text comments on posts (powered by CKEditor)
- Inbuilt contact form on their About Me page — lets other users send them an email via SendGrid

### Admin Accounts
- Grant or revoke Admin/Premium status on any account
- Delete any post, comment, or user account
- Account termination queue (a termination flag gracefully logs the user out and purges their data on next login)

---

## Tech Stack

| Layer | Library / Tool |
|---|---|
| Web framework | [Flask 2.3](https://flask.palletsprojects.com/) |
| ORM | [Flask-SQLAlchemy 3.1](https://flask-sqlalchemy.palletsprojects.com/) + SQLAlchemy 2.0 |
| Auth | [Flask-Login 0.6](https://flask-login.readthedocs.io/) |
| Forms | [Flask-WTF 1.2](https://flask-wtf.readthedocs.io/) + WTForms 3 |
| Rich text editor | [Flask-CKEditor 0.5](https://flask-ckeditor.readthedocs.io/) |
| UI | [Bootstrap-Flask 2.3](https://bootstrap-flask.readthedocs.io/) (Bootstrap 5) |
| Avatars | [Flask-Gravatar 0.5](https://github.com/zzzsochi/Flask-Gravatar) |
| Email | [SendGrid 6.11](https://github.com/sendgrid/sendgrid-python) |
| Database | PostgreSQL (production) via `psycopg2-binary` / SQLite (local dev) |
| WSGI server | [Gunicorn 21](https://gunicorn.org/) |
| Package manager | [uv](https://github.com/astral-sh/uv) |

---

## Project Structure

```
Career-Post/
├── main.py               # Entrypoint — calls create_app() and runs the server
├── app.py                # Application Factory (create_app())
├── extensions.py         # Unattached Flask extension instances
├── authhandler.py        # Env config, @admin_only / @logged_on decorators, terminate()
├── dbhandler.py          # SQLAlchemy models (User, Post, Comment) + DB helper functions
├── forms.py              # WTForms form definitions
├── state.py              # Shared mutable state (year, dark_mode)
├── blueprints/
│   ├── __init__.py
│   ├── auth.py           # Auth routes: register, login, logout, account management
│   ├── posts.py          # Post & comment routes: feed, view, create, edit, delete
│   └── main_bp.py        # Core routes: homepage, about, search, theme, confirm
├── templates/
│   ├── base.html         # Shared layout: navbar, footer, post card grid, flash messages
│   ├── index.html        # Homepage hero + pricing plans
│   ├── viewer.html       # Post viewer & About Me page (shared template)
│   ├── editor.html       # Post / About Me editor sidebar layout
│   ├── posts.html        # Full post feed / search results
│   ├── form.html         # Generic WTForms renderer
│   └── confirm.html      # Destructive-action confirmation page
├── pyrightconfig.json    # Pylance / Pyright config (strict mode, venv path)
├── pyproject.toml        # Project metadata and dependencies (uv)
└── Procfile              # Heroku/Render deployment (gunicorn)
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager
- A PostgreSQL database (or leave `DB_URI` pointing to a local SQLite file for development)
- A [SendGrid](https://sendgrid.com/) account and API key (for the contact-email feature)

### 1. Clone and install dependencies

```bash
git clone https://github.com/TheWhiteLionGod/Career-Post.git
cd Career-Post
uv sync
```

### 2. Set environment variables

| Variable | Description |
|---|---|
| `FLASK_KEY` | Flask secret key (any long random string) |
| `DB_URI` | SQLAlchemy database URI, e.g. `postgresql://user:pass@host/db` |
| `EMAIL` | The admin account email address |
| `SENDGRID` | SendGrid API key |

You can put these in a `.env` file or export them in your shell. The app will raise an `AssertionError` at startup if any are missing.

### 3. Run locally

```bash
uv run python main.py
```

The app creates all database tables automatically on first launch and starts on `http://127.0.0.1:5000`.

---

## Deployment

The project ships with a `Procfile` for Heroku or Render:

```
web: gunicorn main:app
```

Set the four environment variables above in your hosting dashboard and deploy. The `psycopg2-binary` driver is included for PostgreSQL support.

---

## User Roles

| Role | How to Obtain | Capabilities |
|---|---|---|
| **Free** | Register normally | 1 post/day, About Me page |
| **Premium** | Register with `?premium=True` or granted by admin | Unlimited posts, comments, contact form |
| **Admin** | Granted by the `EMAIL` env-var owner | All Premium features + user/content moderation |

> The account whose email matches the `EMAIL` environment variable is automatically promoted to admin on their first login.

---

## Development Notes

- **Type checking**: The project is configured for **strict** mypy and Pylance (Pyright) type checking. Run `uv run mypy .` to check all 11 source files.
- **Code style**: `autopep8` and `flake8` are included as dev dependencies.
- **Import resolution**: `pyrightconfig.json` sets `extraPaths: ["."]` so Pylance resolves root-level modules (`authhandler`, `dbhandler`, etc.) from inside the `blueprints/` package.
