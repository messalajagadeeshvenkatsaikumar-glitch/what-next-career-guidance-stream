# What Next? Career Guidance

Flask career guidance application with a student interest quiz, recommendations, SMTP contact replies, and a MySQL-backed database.

## Run locally

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the MySQL values. Copy `admin/.env.example` to `admin/.env` for the separate admin service. `MYSQL_DATABASE` must name a dedicated application database; never use MySQL's `sys`, `mysql`, `information_schema`, or `performance_schema` schemas.
   For a new, empty MySQL database, set `DB_AUTO_INIT=True` so the app creates its tables and initial seed data. For a managed database that already contains project data, set `DB_AUTO_INIT=False` to prevent schema or seed updates.
3. Start Flask:

   ```powershell
   flask --app app run --debug
   ```

The flowchart is available at `/flowchart`. The health check is available at `/health`. The main site sends its Admin link to `ADMIN_SITE_URL`; the admin service login is `/login`.

## Email delivery

SMTP is used for outgoing contact replies. Configure these values in Render when that feature is deployed; never commit live values:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS` (or `SMTP_USE_SSL`)
- `ADMIN_SITE_URL` on the main service and `MAIN_SITE_URL` on the admin service
- `ADMIN_USERNAME` and preferably `ADMIN_PASSWORD_HASH` on the admin service

The Render Blueprint defaults to STARTTLS (`SMTP_USE_TLS=True`, port `587`). For an SMTP provider that requires implicit SSL, use its SSL port (commonly `465`), set `SMTP_USE_SSL=True`, and set `SMTP_USE_TLS=False`. Keep SMTP credentials in Render environment settings, not in source files.

Set `ADMIN_PASSWORD_HASH` to a Werkzeug-compatible generated hash rather than keeping an administrator password as plain deployment configuration. SMTP is required to send contact replies; delivery failures are reported rather than presented as successful.

Generate the hash locally, then put only its output into Render:

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('choose-a-strong-admin-password'))"
```

## Shared database migration

On startup, the main service applies the additive migration `2026_10_20_admin_otp_and_replies` after verifying the existing core schema, or after creating the schema when `DB_AUTO_INIT=True`. It creates the contact-reply table and `feedback.status`; it does not truncate, recreate, or delete existing records. A newly empty database receives the same structures through `database.sql`. Existing database objects from older application versions are left untouched and are not used by the current application.

For a controlled rollback, first deploy the previous app version and take a database backup. Only after it is no longer needed, remove the migration-created tables (`contact_message_replies` and `schema_migrations`) and then remove `feedback.status`. Do not run those destructive statements against production without a tested backup; the normal rollback is application-only and leaves the additive data intact.

## GitHub to Render deployment

This repository uses MySQL. Render's web service does not provide a persistent MySQL database for this configuration, so create a managed MySQL database with a provider before deploying the web service. Do not use `database/local.sqlite3` for production data.

1. Push the repository to GitHub. Its root must contain `app.py`, `admin/`, `render.yaml`, `database.sql`, and `requirements.txt`.
2. In Render, choose **New + > Blueprint**, connect `messalajagadeeshvenkatsaikumar-glitch/what-next-career-guidance-stream`, and select the branch to deploy. The root `render.yaml` defines two separate web services from this same repository: `what-next-career-guidance` and `what-next-career-guidance-admin`.
3. For each service, provide the same managed MySQL values: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`. The Blueprint uses `MYSQL_SSL_MODE=REQUIRED` and leaves `MYSQL_SSL_CA` empty. If Render has an old `MYSQL_SSL_CA` value or a `VERIFY_CA`/`VERIFY_IDENTITY` mode configured, clear the CA path and restore `MYSQL_SSL_MODE=REQUIRED`, then redeploy. To use certificate verification instead, configure a CA certificate as a Render Secret File and set `MYSQL_SSL_CA` to its deployed path; a local file path is not available in Render.
4. `DB_AUTO_INIT` is `False` by default to preserve an existing managed database. Set it to `True` only for a new, empty database. Wait until the main service's `/health` check succeeds before relying on the admin dashboard; this applies the additive migration safely.
5. Set `ADMIN_SITE_URL` on the main service and `MAIN_SITE_URL` on the admin service to their actual public URLs. Set an explicit `ADMIN_USERNAME` plus `ADMIN_PASSWORD_HASH` (preferred) on the admin service. Sign in at the admin service's `/login`.
6. Both services have `/health` checks. A successful response is JSON with `{"status":"ok","database":"connected"}`. The main site's health check also verifies all required application tables; database failures return HTTP 503 rather than reporting a successful deployment.
7. Subsequent pushes to the connected GitHub branch trigger Render deployments for both services. Check each service's Render Events and Logs to confirm its build, health check, and deployment.

If Render reports a port-scan timeout, check the service logs for the `Starting Gunicorn on 0.0.0.0:<port>` message and any following Gunicorn startup error before changing the port. The main service reads Render's `PORT` and passes it directly to Gunicorn without relying on shell variable expansion.
Do not set a conflicting port in Render's service settings; the launcher uses Render's `PORT` value (and defaults to `5000` only when running outside Render).

## Deployment flow

```text
GitHub push
    -> Render Blueprint (two web services)
    -> main service: python run_server.py (binds Gunicorn to Render's PORT)
    -> admin service: gunicorn --chdir admin/admin_site app:app
    -> both services connect to the same managed MySQL database
    -> main service initializes database.sql for a new database
    -> students register, take the quiz, and receive recommendations
```

Never commit `.env`, database passwords, private certificates, or generated secret values. Use Render environment variables for production secrets.

## Verify the database safely

From this directory, run `python test_db_connection.py`. It performs only `SELECT` queries and reports whether the configured dedicated database is reachable. The application also performs a schema-readiness check before serving database-backed pages, so a wrong database selection produces a clear 503 response instead of an internal server error.
