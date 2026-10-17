# What Next? Career Guidance

Flask career guidance application with a student interest quiz, recommendations, an admin question API, and a MySQL-backed dashboard.

## Run locally

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the MySQL and admin values. `MYSQL_DATABASE` must name a dedicated application database; never use MySQL's `sys`, `mysql`, `information_schema`, or `performance_schema` schemas.
   For a new, empty MySQL database, set `DB_AUTO_INIT=True` so the app creates its tables and initial seed data. For a managed database that already contains project data, set `DB_AUTO_INIT=False` to prevent schema or seed updates.
3. Start Flask:

   ```powershell
   flask --app app run --debug
   ```

The flowchart is available at `/flowchart`. The health check is available at `/health`.

## GitHub to Render deployment

This repository uses MySQL. Render's web service does not provide a persistent MySQL database for this configuration, so create a managed MySQL database with a provider before deploying the web service. Do not use `database/local.sqlite3` for production data.

1. Push this folder's contents to a GitHub repository. The repository root must contain `app.py`, `render.yaml`, `database.sql`, and `requirements.txt`.
2. In the Render dashboard choose **New + > Blueprint**, connect GitHub, select the repository, and choose the branch to deploy.
3. Render reads `render.yaml`, installs `requirements.txt`, starts Gunicorn, and checks `/health`.
4. In the Render service environment, set the `MYSQL_*` values from the managed MySQL provider:
   `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, and `MYSQL_SSL_MODE=REQUIRED`.
5. Keep `SECRET_KEY` and `ADMIN_PASSWORD` generated or replace them with long secret values. Set `MAIN_SITE_URL` to the Render service URL and `CORS_ALLOWED_ORIGINS` to the allowed frontend origin.
6. For a new, empty managed MySQL database, leave the Render Blueprint's `DB_AUTO_INIT=True` setting enabled so the app creates the schema and seed data on its first request. For an existing database, verify its tables and set `DB_AUTO_INIT=False` before deploying.
7. Visit `/health`. A successful response is JSON with `{"status":"ok","database":"connected"}`. The check verifies both the connection and every required application table. On failure, `/health` returns a sanitized actionable `message`; website pages show the same error in a service-unavailable page, while API requests receive JSON.
8. Visit `/admin/setup` once, then sign in at `/admin/login` using `ADMIN_USERNAME` and `ADMIN_PASSWORD`. Remove or protect this setup endpoint after the first administrator is created.

## Deployment flow

```text
GitHub push
    -> Render Blueprint
    -> pip install -r requirements.txt
    -> gunicorn --bind 0.0.0.0:$PORT app:app
    -> /health checks the MySQL connection
    -> first request initializes database.sql
    -> students register, take the quiz, and receive recommendations
```

Never commit `.env`, database passwords, private certificates, or generated secret values. Use Render environment variables for production secrets.

## Verify the database safely

From this directory, run `python test_db_connection.py`. It performs only `SELECT` queries and reports whether the configured dedicated database is reachable. The application also performs a schema-readiness check before serving database-backed pages, so a wrong database selection produces a clear 503 response instead of an internal server error.
