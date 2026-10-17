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

1. Push the repository to GitHub. Its root must contain `app.py`, `admin/`, `render.yaml`, `database.sql`, and `requirements.txt`.
2. In Render, choose **New + > Blueprint**, connect `messalajagadeeshvenkatsaikumar-glitch/what-next-career-guidance-stream`, and select the branch to deploy. The root `render.yaml` defines two separate web services from this same repository: `what-next-career-guidance` and `what-next-career-guidance-admin`.
3. For each service, provide the same managed MySQL values: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`. Keep `MYSQL_SSL_MODE=REQUIRED` and leave `MYSQL_SSL_CA` unset unless you configure a CA certificate file.
4. The main service initializes a new, empty database when `DB_AUTO_INIT=True`. For an existing database, verify its tables and set `DB_AUTO_INIT=False`. Wait until the main service's `/health` check succeeds before relying on the admin dashboard.
5. Set `MAIN_SITE_URL` on the admin service to the main service's public Render URL. Set the admin service's `ADMIN_PASSWORD` to a strong secret in Render; its `ADMIN_USERNAME` defaults to `admin`. Sign in at the admin service's `/login`.
6. Both services have `/health` checks. A successful response is JSON with `{"status":"ok","database":"connected"}`. The main site's health check also verifies all required application tables; database failures return HTTP 503 rather than reporting a successful deployment.
7. Subsequent pushes to the connected GitHub branch trigger Render deployments for both services. Check each service's Render Events and Logs to confirm its build, health check, and deployment.

## Deployment flow

```text
GitHub push
    -> Render Blueprint (two web services)
    -> main service: gunicorn app:app
    -> admin service: gunicorn --chdir admin/admin_site app:app
    -> both services connect to the same managed MySQL database
    -> main service initializes database.sql for a new database
    -> students register, take the quiz, and receive recommendations
```

Never commit `.env`, database passwords, private certificates, or generated secret values. Use Render environment variables for production secrets.

## Verify the database safely

From this directory, run `python test_db_connection.py`. It performs only `SELECT` queries and reports whether the configured dedicated database is reachable. The application also performs a schema-readiness check before serving database-backed pages, so a wrong database selection produces a clear 503 response instead of an internal server error.
